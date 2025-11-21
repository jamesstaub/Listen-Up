/**
 * AUDIO MODULE
 * Contains Web Audio API functions, oscillator management, and audio processing
 * Refactored to use modular DSP classes
 */

import { AppState, updateAppState, WAVETABLE_SIZE } from './config.js';
import { calculateFrequency, generateFilenameParts, showStatus } from './utils.js';
import { clearCustomWaveCache } from './visualization.js';
import { AudioEngine, WavetableManager, WAVExporter } from './dsp/index.js';

// ================================
// DSP INSTANCES
// ================================

let audioEngine = null;
let wavetableManager = null;

// ================================
// AUDIO INITIALIZATION
// ================================

/**
 * Initializes the AudioContext and the audio graph
 */
export function initAudio() {
    if (!audioEngine) {
        audioEngine = new AudioEngine();
        wavetableManager = new WavetableManager();
        
        // Initialize the audio engine
        audioEngine.initialize(AppState.masterGainValue);
        
        // Store references for compatibility
        AppState.audioContext = audioEngine.getContext();
        AppState.compressor = audioEngine.compressor;
        AppState.masterGain = audioEngine.masterGain;
        
        // Store standard waveforms for compatibility
        AppState.blWaveforms = AppState.blWaveforms || {};
        AppState.blWaveforms.square = audioEngine.getStandardWaveform('square');
        AppState.blWaveforms.sawtooth = audioEngine.getStandardWaveform('sawtooth');
        AppState.blWaveforms.triangle = audioEngine.getStandardWaveform('triangle');
    }
    
    // Resume context if suspended
    audioEngine.resume();
}

// ================================
// OSCILLATOR MANAGEMENT
// ================================

/**
 * Starts all oscillators for the current harmonic configuration
 */
export function startTone() {
    initAudio();
    if (AppState.isPlaying) return;

    // Create oscillators for each harmonic
    for (let i = 0; i < AppState.harmonicAmplitudes.length; i++) {
        const amplitude = AppState.harmonicAmplitudes[i];
        const ratio = AppState.currentSystem.ratios[i];
        
        if (amplitude > 0 && ratio > 0) {
            const frequency = calculateFrequency(ratio);
            const gain = amplitude * AppState.masterGainValue;
            
            // Determine waveform
            let waveform = AppState.currentWaveform;
            if (waveform.startsWith('custom_')) {
                // Use custom waveform from wavetable manager
                const customWave = wavetableManager.getWaveform(waveform);
                if (customWave) {
                    waveform = customWave;
                } else {
                    waveform = 'sine'; // Fallback
                }
            }
            
            // Create and start oscillator using AudioEngine
            const oscData = audioEngine.createOscillator(frequency, waveform, gain);
            const oscKey = `osc_${i}`;
            audioEngine.addOscillator(oscKey, oscData);
            
            // Store for compatibility
            AppState.oscillators.push({ 
                osc: oscData.oscillator, 
                gainNode: oscData.gainNode, 
                ratio,
                key: oscKey 
            });
        }
    }

    updateAppState({ isPlaying: true });
}

/**
 * Stops all oscillators
 */
export function stopTone() {
    if (!AppState.isPlaying || !audioEngine) return;

    // Stop all oscillators using AudioEngine
    audioEngine.stopAllOscillators();

    updateAppState({ 
        oscillators: [],
        isPlaying: false 
    });
}

/**
 * Updates the frequency and gain of all active oscillators
 */
export function updateAudioProperties() {
    if (!AppState.isPlaying || !audioEngine) return;

    const rampTime = 0.02; // Shorter ramp time since we have momentum smoothing

    // Update Master Gain
    audioEngine.updateMasterGain(AppState.masterGainValue, rampTime);

    // Update individual oscillators
    AppState.oscillators.forEach((node, i) => {
        if (node.key) {
            const ratio = AppState.currentSystem.ratios[i];
            const newFreq = calculateFrequency(ratio);
            const newGain = AppState.harmonicAmplitudes[i] * AppState.masterGainValue;

            // Use AudioEngine methods for smooth updates
            audioEngine.updateOscillatorFrequency(node.key, newFreq, rampTime);
            audioEngine.updateOscillatorGain(node.key, Math.max(0.001, newGain), rampTime);
        }
    });
}

/**
 * Restarts the audio with current settings (useful when changing waveforms)
 */
export function restartAudio() {
    if (AppState.isPlaying) {
        stopTone();
        setTimeout(startTone, 50);
    }
}

// ================================
// WAVETABLE GENERATION
// ================================

/**
 * Samples the current waveform configuration into a buffer
 * @returns {Float32Array} Sampled waveform buffer
 */
export function sampleCurrentWaveform() {
    const buffer = new Float32Array(WAVETABLE_SIZE);
    let maxAmplitude = 0;
    
    const p = AppState.p5Instance;
    
    if (!p || !p.getWaveValue) {
        console.error("Wavetable Error: p5 context not initialized or missing getWaveValue function");
        showStatus("Export failed: Visualization is not fully initialized. Try playing the tone first.", 'error');
        return new Float32Array(0);
    }
    
    if (!AppState.currentSystem || !AppState.currentSystem.ratios || AppState.harmonicAmplitudes.length === 0) {
        console.error("Wavetable Error: Spectral system data is missing or incomplete");
        showStatus("Export failed: Spectral data (ratios/amplitudes) is missing.", 'error');
        return new Float32Array(0);
    }
    
    for (let i = 0; i < WAVETABLE_SIZE; i++) {
        const theta = p.map(i, 0, WAVETABLE_SIZE, 0, p.TWO_PI);
        
        let summedWave = 0;

        for (let h = 0; h < AppState.harmonicAmplitudes.length; h++) {
            const ratio = AppState.currentSystem.ratios[h];
            const amp = AppState.harmonicAmplitudes[h];
            
            summedWave += p.getWaveValue(AppState.currentWaveform, ratio * theta) * amp;
        }
        
        buffer[i] = summedWave;
        maxAmplitude = Math.max(maxAmplitude, Math.abs(summedWave));
    }

    // Normalize the buffer
    if (maxAmplitude > 0) {
        const normalizationFactor = 1.0 / maxAmplitude;
        for (let i = 0; i < WAVETABLE_SIZE; i++) {
            buffer[i] *= normalizationFactor;
        }
    }
    
    return buffer;
}

// ================================
// WAVETABLE EXPORT
// ================================

/**
 * Exports a waveform buffer as a WAV file
 * @param {Float32Array} buffer - Waveform buffer to export
 * @param {number} numCycles - Number of cycles to export
 */
export function exportAsWAV(buffer, numCycles = 1) {
    if (!AppState.audioContext) {
        showStatus("Error: Audio system not initialized. Please click 'Start Tone' first.", 'error');
        return;
    }
    if (buffer.length === 0) {
        showStatus("WAV Export Failed: Cannot export empty waveform data.", 'error');
        return;
    }
    
    const sampleRate = AppState.audioContext.sampleRate;

    // Generate filename
    const parts = generateFilenameParts();
    const filename = [
        parts.noteLetter,
        parts.waveform,
        parts.systemName,
        parts.levels,
        parts.subharmonicFlag
    ].filter(Boolean).join('-') + '.wav';

    try {
        // Use WAVExporter class
        WAVExporter.exportAsWAV(buffer, sampleRate, filename, numCycles);
        showStatus(`Wavetable exported as ${filename}!`, 'success');
    } catch (error) {
        showStatus(`WAV Export Failed: ${error.message}`, 'error');
    }
}

// ================================
// CUSTOM WAVEFORM MANAGEMENT
// ================================

/**
 * Adds a sampled waveform to the list of available waveforms
 * @param {Float32Array} sampledBuffer - Sampled waveform data
 */
export function addToWaveforms(sampledBuffer) {
    initAudio();
    if (sampledBuffer.length === 0) {
        showStatus("Warning: Cannot add empty waveform data.", 'warning');
        return;
    }

    try {
        // Use WavetableManager to add the new waveform
        const waveKey = wavetableManager.addFromSamples(sampledBuffer, AppState.audioContext);
        
        // Store in legacy format for compatibility
        const coefficients = wavetableManager.getCoefficients(waveKey);
        const periodicWave = wavetableManager.getWaveform(waveKey);
        
        AppState.blWaveforms[waveKey] = periodicWave;
        if (!AppState.customWaveCoefficients) {
            AppState.customWaveCoefficients = {};
        }
        AppState.customWaveCoefficients[waveKey] = coefficients;
        AppState.customWaveCount = wavetableManager.getCount();

        // Clear visualization cache to ensure fresh calculations
        clearCustomWaveCache();

        // Generate UI name
        const parts = generateFilenameParts();
        const optionName = `${parts.noteLetter}-${parts.waveform}-${parts.systemName}-${parts.levels}` + 
                          (parts.subharmonicFlag ? `-${parts.subharmonicFlag}` : '');

        // Add to UI
        const select = document.getElementById('waveform-select');
        if (select) {
            const option = document.createElement('option');
            option.textContent = `Custom ${AppState.customWaveCount}: ${optionName}`;
            option.value = waveKey;
            select.appendChild(option);
            
            // Select the new waveform automatically
            updateAppState({ currentWaveform: waveKey });
            select.value = waveKey;
        }
        
        showStatus(`Successfully added new waveform: Custom ${AppState.customWaveCount}. Now synthesizing with it!`, 'success');

        if (AppState.isPlaying) {
            restartAudio();
        }
    } catch (error) {
        showStatus(`Failed to add waveform: ${error.message}`, 'error');
    }
}