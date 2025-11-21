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
export async function initAudio() {
    if (!audioEngine) {
        audioEngine = new AudioEngine();
        wavetableManager = new WavetableManager();
        
        // Initialize the audio engine (async) - temporarily disable AudioWorklet for debugging
        await audioEngine.initialize(AppState.masterGainValue, { useAudioWorklet: false });
        
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
    await audioEngine.resume();
}

// ================================
// SYNTHESIS HELPERS
// ================================

/**
 * Resolves waveform parameter to a proper Web Audio API format
 * @param {string} waveformName - Waveform name from AppState
 * @returns {string|PeriodicWave} Resolved waveform
 */
function resolveWaveform(waveformName) {
    if (!waveformName) {
        return 'sine';
    }
    
    if (waveformName.startsWith('custom_')) {
        const customWave = wavetableManager.getWaveform(waveformName);
        return customWave || 'sine';
    }
    
    return waveformName;
}

// ================================
// OSCILLATOR MANAGEMENT
// ================================

/**
 * Starts synthesis using the appropriate method (AudioWorklet or oscillators)
 */
export async function startTone() {
    await initAudio();
    if (AppState.isPlaying) return;

    try {
        if (audioEngine.isUsingAudioWorklet()) {
            await startToneWithWorklet();
        } else {
            await startToneWithOscillators();
        }
        updateAppState({ isPlaying: true });
    } catch (error) {
        console.error('Failed to start synthesis:', error);
        throw error;
    }
}

/**
 * AudioWorklet-based synthesis
 */
async function startToneWithWorklet() {
    const success = audioEngine.startSynthesis(
        AppState.harmonicAmplitudes,
        AppState.currentSystem.ratios,
        AppState.fundamentalFrequency,
        AppState.currentWaveform
    );
    
    if (!success) {
        throw new Error('AudioWorklet synthesis failed');
    }
}

/**
 * Individual oscillator-based synthesis
 */
async function startToneWithOscillators() {
    // Clear any existing oscillators
    AppState.oscillators = [];
    
    // Create oscillators for all harmonics
    for (let i = 0; i < AppState.currentSystem.ratios.length; i++) {
        const ratio = AppState.currentSystem.ratios[i];
        const amplitude = AppState.harmonicAmplitudes[i] || 0;
        
        if (ratio > 0) {
            const frequency = calculateFrequency(ratio);
            const gain = amplitude * AppState.masterGainValue;
            const waveform = resolveWaveform(AppState.currentWaveform);
            
            try {
                const oscData = audioEngine.createOscillator(frequency, waveform, gain);
                const oscKey = `harmonic_${i}`;
                audioEngine.addOscillator(oscKey, oscData);
                
                // Ensure array is properly sized
                while (AppState.oscillators.length <= i) {
                    AppState.oscillators.push(null);
                }
                
                AppState.oscillators[i] = { 
                    key: oscKey,
                    ratio: ratio
                };
            } catch (error) {
                console.error(`Failed to create oscillator ${i}:`, error);
                AppState.oscillators[i] = null;
            }
        } else {
            AppState.oscillators[i] = null;
        }
    }
}

/**
 * Fallback oscillator-based synthesis for compatibility
 */
async function startToneOscillatorFallback() {
    // Legacy function - delegate to new implementation
    await startToneWithOscillators();
}

/**
 * Stops all synthesis
 */
export function stopTone() {
    if (!AppState.isPlaying || !audioEngine) return;

    // Use appropriate stop method based on synthesis mode
    if (audioEngine.isUsingAudioWorklet()) {
        audioEngine.stopSynthesis();
    } else {
        // Stop individual oscillators
        audioEngine.stopAllOscillators();
    }

    updateAppState({ 
        oscillators: [],
        isPlaying: false 
    });
}

/**
 * Updates synthesis parameters in real-time
 */
export function updateAudioProperties() {
    if (!AppState.isPlaying || !audioEngine) return;

    const rampTime = 0.02; // Shorter ramp time since we have momentum smoothing

    if (audioEngine.isUsingAudioWorklet()) {
        updateAudioPropertiesWithWorklet();
    } else {
        updateAudioPropertiesOscillatorFallback(rampTime);
    }
}

/**
 * Updates AudioWorklet synthesis parameters
 */
function updateAudioPropertiesWithWorklet() {
    try {
        audioEngine.updateSynthesis(
            AppState.harmonicAmplitudes,
            AppState.currentSystem.ratios,
            AppState.fundamentalFrequency,
            AppState.masterGainValue
        );
    } catch (error) {
        console.error('AudioWorklet update failed:', error);
    }
}

/**
 * Updates oscillator parameters for individual oscillator synthesis
 */
function updateAudioPropertiesOscillatorFallback(rampTime) {
    // Update Master Gain
    audioEngine.updateMasterGain(AppState.masterGainValue, rampTime);

    // Update existing oscillators (gain and frequency)
    AppState.oscillators.forEach((node, i) => {
        if (node && node.key) {
            const ratio = AppState.currentSystem.ratios[i];
            const newFreq = calculateFrequency(ratio);
            const amplitude = AppState.harmonicAmplitudes[i] || 0;
            const newGain = amplitude * AppState.masterGainValue;

            // Use AudioEngine methods for smooth updates
            audioEngine.updateOscillatorFrequency(node.key, newFreq, rampTime);
            audioEngine.updateOscillatorGain(node.key, Math.max(0.0001, newGain), rampTime);
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
 * Uses AudioWorklet sampling when available for accurate capture
 * @returns {Float32Array} Sampled waveform buffer
 */
export async function sampleCurrentWaveform() {
    await initAudio();
    
    // Try AudioEngine sampling first (supports AudioWorklet)
    if (audioEngine && audioEngine.isUsingAudioWorklet()) {
        try {
            return await audioEngine.sampleCurrentWaveform(WAVETABLE_SIZE);
        } catch (error) {
            console.warn('AudioEngine sampling failed, falling back to basic method:', error);
            // Fall through to basic sampling
        }
    }
    
    // Fallback to basic harmonic synthesis sampling
    return sampleCurrentWaveformBasic();
}

/**
 * Basic waveform sampling using harmonic synthesis
 * @returns {Float32Array} Sampled waveform buffer
 */
function sampleCurrentWaveformBasic() {
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
export async function addToWaveforms(sampledBuffer) {
    await initAudio();
    if (sampledBuffer.length === 0) {
        showStatus("Warning: Cannot add empty waveform data.", 'warning');
        return;
    }

    try {
        // Use WavetableManager to add the new waveform
        const waveKey = wavetableManager.addFromSamples(sampledBuffer, AppState.audioContext);
        
        // Send the custom waveform to AudioEngine (for AudioWorklet support)
        if (audioEngine) {
            audioEngine.addCustomWaveform(waveKey, sampledBuffer);
        }
        
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