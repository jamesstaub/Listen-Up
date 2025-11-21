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

/**
 * Gets the frequency correction factor for custom waveforms
 * @param {string} waveformName - Waveform name from AppState
 * @returns {number} Frequency multiplier (1/periodMultiplier)
 */
function getFrequencyCorrection(waveformName) {
    if (!waveformName || !waveformName.startsWith('custom_')) {
        return 1;
    }
    
    // Get period multiplier from WavetableManager or AppState
    let periodMultiplier = 1;
    if (wavetableManager) {
        periodMultiplier = wavetableManager.getPeriodMultiplier(waveformName);
    } else if (AppState.customWavePeriodMultipliers) {
        periodMultiplier = AppState.customWavePeriodMultipliers[waveformName] || 1;
    }
    
    // Frequency correction is inverse of period multiplier
    return 1 / periodMultiplier;
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
            const frequencyCorrection = getFrequencyCorrection(AppState.currentWaveform);
            const correctedFrequency = frequency * frequencyCorrection;
            
            console.log(`Oscillator ${i}: base freq=${frequency}Hz, correction=${frequencyCorrection}, final=${correctedFrequency}Hz`);
            
            try {
                const oscData = audioEngine.createOscillator(correctedFrequency, waveform, gain);
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
            const baseFreq = calculateFrequency(ratio);
            const frequencyCorrection = getFrequencyCorrection(AppState.currentWaveform);
            const newFreq = baseFreq * frequencyCorrection;
            const amplitude = AppState.harmonicAmplitudes[i] || 0;
            const newGain = amplitude * AppState.masterGainValue;

            // Use AudioEngine methods for smooth updates
            audioEngine.updateOscillatorFrequency(node.key, newFreq, rampTime);
            audioEngine.updateOscillatorGain(node.key, newGain, rampTime);
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
 * @returns {Object} {buffer: Float32Array, periodMultiplier: number}
 */
export async function sampleCurrentWaveform() {
    await initAudio();
    
    // Try AudioEngine sampling first (supports AudioWorklet)
    if (audioEngine && audioEngine.isUsingAudioWorklet()) {
        try {
            const buffer = await audioEngine.sampleCurrentWaveform(WAVETABLE_SIZE);
            return { buffer, periodMultiplier: 1 }; // AudioWorklet doesn't use period multiplier
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
 * @returns {Object} {buffer: Float32Array, periodMultiplier: number}
 */
function sampleCurrentWaveformBasic() {
    const buffer = new Float32Array(WAVETABLE_SIZE);
    let maxAmplitude = 0;
    
    const p = AppState.p5Instance;
    
    if (!p || !p.getWaveValue) {
        console.error("Wavetable Error: p5 context not initialized or missing getWaveValue function");
        showStatus("Export failed: Visualization is not fully initialized. Try playing the tone first.", 'error');
        return { buffer: new Float32Array(0), periodMultiplier: 1 };
    }
    
    if (!AppState.currentSystem || !AppState.currentSystem.ratios || AppState.harmonicAmplitudes.length === 0) {
        console.error("Wavetable Error: Spectral system data is missing or incomplete");
        showStatus("Export failed: Spectral data (ratios/amplitudes) is missing.", 'error');
        return { buffer: new Float32Array(0), periodMultiplier: 1 };
    }
    
    console.log('Sampling waveform with system:', AppState.currentSystem.name);
    
    // Get active ratios
    const activeRatios = [];
    for (let h = 0; h < AppState.harmonicAmplitudes.length; h++) {
        if (AppState.harmonicAmplitudes[h] > 0.001) {
            activeRatios.push(AppState.currentSystem.ratios[h]);
        }
    }
    console.log('Active ratios:', activeRatios);
    
    // Calculate the period multiplier to minimize discontinuity
    const periodMultiplier = calculateOptimalPeriod(activeRatios);
    console.log('Period multiplier:', periodMultiplier);
    
    // The optimal period is periodMultiplier times the fundamental period
    // We sample one full cycle of this longer period
    const totalPeriodLength = p.TWO_PI * periodMultiplier;
    
    for (let i = 0; i < WAVETABLE_SIZE; i++) {
        // Sample one complete period of the optimal period length
        const theta = p.map(i, 0, WAVETABLE_SIZE, 0, totalPeriodLength);
        
        let summedWave = 0;

        for (let h = 0; h < AppState.harmonicAmplitudes.length; h++) {
            const ratio = AppState.currentSystem.ratios[h];
            const amp = AppState.harmonicAmplitudes[h];
            
            if (amp > 0.001) { // Only include audible components
                // The ratio remains unchanged - we're just sampling over a longer period
                summedWave += p.getWaveValue(AppState.currentWaveform, ratio * theta) * amp;
            }
        }
        
        buffer[i] = summedWave;
        maxAmplitude = Math.max(maxAmplitude, Math.abs(summedWave));
    }

    // Check for continuity
    const startValue = buffer[0];
    const endValue = buffer[buffer.length - 1];
    const discontinuity = Math.abs(endValue - startValue);
    console.log(`Wavetable discontinuity: ${discontinuity} (start: ${startValue}, end: ${endValue})`);
    
    // Report if we achieved good continuity
    if (discontinuity < 0.01) {
        console.log('✓ Good continuity achieved');
    } else {
        console.log('⚠ Still has discontinuity - may cause buzzing');
    }

    // Normalize the buffer
    if (maxAmplitude > 0) {
        const normalizationFactor = 1.0 / maxAmplitude;
        for (let i = 0; i < WAVETABLE_SIZE; i++) {
            buffer[i] *= normalizationFactor;
        }
    }
    
    console.log(`Sampled ${buffer.length} points, max amplitude: ${maxAmplitude}`);
    
    return { buffer, periodMultiplier };
}

/**
 * Calculate optimal period multiplier to minimize phase discontinuities
 * @param {Array} ratios - Active frequency ratios
 * @returns {number} Period multiplier
 */
function calculateOptimalPeriod(ratios) {
    if (ratios.length === 0) return 1;
    
    // For each ratio, find the smallest integer period where ratio * period ≈ integer
    const bestPeriods = ratios.map(ratio => {
        let bestPeriod = 1;
        let smallestError = Infinity;
        
        // Test periods 1-20
        for (let period = 1; period <= 20; period++) {
            const cycles = ratio * period;
            const fractionalPart = Math.abs(cycles - Math.round(cycles));
            
            if (fractionalPart < smallestError) {
                smallestError = fractionalPart;
                bestPeriod = period;
            }
            
            // If we found an exact match, stop
            if (fractionalPart < 0.001) break;
        }
        
        console.log(`Ratio ${ratio}: best period ${bestPeriod} gives ${ratio * bestPeriod} cycles (error: ${smallestError})`);
        return bestPeriod;
    });
    
    // Use the LCM of all best periods
    const lcm = bestPeriods.reduce((acc, period) => {
        const gcd = (a, b) => b === 0 ? a : gcd(b, a % b);
        return (acc * period) / gcd(acc, period);
    }, 1);
    
    // Cap at reasonable value
    return Math.min(lcm, 20);
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
export async function addToWaveforms(sampledData) {
    await initAudio();
    
    // Handle both old format (just buffer) and new format (object with buffer + periodMultiplier)
    const buffer = sampledData.buffer || sampledData;
    const periodMultiplier = sampledData.periodMultiplier || 1;
    
    if (buffer.length === 0) {
        showStatus("Warning: Cannot add empty waveform data.", 'warning');
        return;
    }

    try {
        // Use WavetableManager to add the new waveform with period multiplier
        const waveKey = wavetableManager.addFromSamples(buffer, AppState.audioContext, 128, periodMultiplier);
        
        // Send the custom waveform to AudioEngine (for AudioWorklet support)
        if (audioEngine) {
            audioEngine.addCustomWaveform(waveKey, buffer);
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

        // Store period multiplier in AppState for frequency correction
        if (!AppState.customWavePeriodMultipliers) {
            AppState.customWavePeriodMultipliers = {};
        }
        AppState.customWavePeriodMultipliers[waveKey] = periodMultiplier;
        
        console.log(`Stored waveform ${waveKey} with period multiplier ${periodMultiplier}`);

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