/**
 * AUDIO MODULE
 * Contains Web Audio API functions, oscillator management, and audio processing
 */

import { AppState, updateAppState, WAVETABLE_SIZE } from './config.js';
import { calculateFrequency, generateFilenameParts, showStatus } from './utils.js';

// ================================
// AUDIO INITIALIZATION
// ================================

/**
 * Initializes the AudioContext and the audio graph
 */
export function initAudio() {
    if (!AppState.audioContext) {
        AppState.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        
        // Pre-calculate band-limited waveforms
        AppState.blWaveforms.square = createBandLimitedWaveform(AppState.audioContext, 'square');
        AppState.blWaveforms.sawtooth = createBandLimitedWaveform(AppState.audioContext, 'sawtooth');
        AppState.blWaveforms.triangle = createBandLimitedWaveform(AppState.audioContext, 'triangle');

        // Create dynamics compressor
        AppState.compressor = AppState.audioContext.createDynamicsCompressor();
        AppState.compressor.threshold.setValueAtTime(-12, AppState.audioContext.currentTime);
        AppState.compressor.ratio.setValueAtTime(12, AppState.audioContext.currentTime);

        // Create master gain node
        AppState.masterGain = AppState.audioContext.createGain();
        AppState.masterGain.gain.setValueAtTime(AppState.masterGainValue, AppState.audioContext.currentTime);
        AppState.masterGain.maxGain = 1.0;

        // Connect the audio graph
        AppState.compressor.connect(AppState.masterGain);
        AppState.masterGain.connect(AppState.audioContext.destination);
    }
    
    // Resume context if suspended (needed for some browsers like Chrome)
    if (AppState.audioContext.state === 'suspended') {
        AppState.audioContext.resume();
    }
}

// ================================
// WAVEFORM GENERATION
// ================================

/**
 * Generates a PeriodicWave for a band-limited waveform (Square, Sawtooth, or Triangle)
 * @param {AudioContext} context - Audio context
 * @param {string} type - Waveform type ('square', 'sawtooth', 'triangle')
 * @returns {PeriodicWave} Generated periodic wave
 */
function createBandLimitedWaveform(context, type) {
    const maxHarmonics = 1024;
    const real = new Float32Array(maxHarmonics + 1);
    const imag = new Float32Array(maxHarmonics + 1);

    for (let n = 1; n <= maxHarmonics; n++) {
        let amplitude = 0;
        let sign = 1;

        switch (type) {
            case 'square':
                if (n % 2 !== 0) {
                    amplitude = 4 / (Math.PI * n);
                }
                break;
            case 'sawtooth':
                amplitude = 2 / (Math.PI * n);
                sign = (n % 2 === 0) ? -1 : 1;
                break;
            case 'triangle':
                if (n % 2 !== 0) {
                    amplitude = 8 / (Math.PI * Math.PI * n * n);
                    const k = (n - 1) / 2;
                    sign = (k % 2 === 0) ? 1 : -1;
                }
                break;
        }
        imag[n] = amplitude * sign;
    }
    return context.createPeriodicWave(real, imag, { disableNormalization: false });
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

    const now = AppState.audioContext.currentTime;
    
    for (let i = 0; i < AppState.harmonicAmplitudes.length; i++) {
        const ratio = AppState.currentSystem.ratios[i];
        const gainValue = AppState.harmonicAmplitudes[i];
        
        const osc = AppState.audioContext.createOscillator();
        const gainNode = AppState.audioContext.createGain();
        
        // Set waveform: Use PeriodicWave if available, otherwise default to sine
        if (AppState.currentWaveform === 'sine') {
            osc.type = 'sine';
        } else if (AppState.blWaveforms[AppState.currentWaveform]) {
            // Use the PeriodicWave object (pre-calculated BL or custom-exported)
            osc.setPeriodicWave(AppState.blWaveforms[AppState.currentWaveform]);
        } else {
            // Fallback to sine if the selected waveform doesn't exist
            osc.type = 'sine';
        }

        osc.frequency.setValueAtTime(calculateFrequency(ratio), now);
        // Partial gain is relative to the masterGainValue
        gainNode.gain.setValueAtTime(gainValue * AppState.masterGainValue, now);
        
        osc.connect(gainNode);
        gainNode.connect(AppState.compressor);
        
        osc.start(now);
        
        AppState.oscillators.push({ osc, gainNode, ratio });
    }

    updateAppState({ isPlaying: true });
}

/**
 * Stops all oscillators
 */
export function stopTone() {
    if (!AppState.isPlaying || !AppState.audioContext) return;

    const now = AppState.audioContext.currentTime;

    AppState.oscillators.forEach(node => {
        node.gainNode.gain.setValueAtTime(node.gainNode.gain.value, now);
        node.gainNode.gain.linearRampToValueAtTime(0.0001, now + 0.05);
        node.osc.stop(now + 0.06);
        node.osc.disconnect();
        node.gainNode.disconnect();
    });

    updateAppState({ 
        oscillators: [],
        isPlaying: false 
    });
}

/**
 * Updates the frequency and gain of all active oscillators
 */
export function updateAudioProperties() {
    if (!AppState.isPlaying || !AppState.audioContext) return;

    const now = AppState.audioContext.currentTime;
    const rampTime = 0.02; // Shorter ramp time since we have momentum smoothing

    // Update Master Gain with exponential ramp (smoother for audio)
    AppState.masterGain.gain.exponentialRampToValueAtTime(
        Math.max(0.001, AppState.masterGainValue), // Prevent zero values for exponential ramp
        now + rampTime
    );

    AppState.oscillators.forEach((node, i) => {
        const ratio = AppState.currentSystem.ratios[i];
        const newFreq = calculateFrequency(ratio);
        const newGain = AppState.harmonicAmplitudes[i] * AppState.masterGainValue;

        // Use exponential ramp for frequency (sounds more natural)
        node.osc.frequency.exponentialRampToValueAtTime(
            Math.max(0.1, newFreq), // Prevent zero/negative values for exponential ramp
            now + rampTime
        );
        
        // Special handling for gain: use linear ramp for very small values to avoid artifacts
        const targetGain = Math.max(0.0001, newGain);
        
        // Always use exponential for gain changes since momentum smoothing handles the larger changes
        node.gainNode.gain.exponentialRampToValueAtTime(targetGain, now + rampTime);
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
    const cycleLength = buffer.length;
    const totalLength = cycleLength * numCycles;
    const fullBuffer = new Float32Array(totalLength);
    
    for (let i = 0; i < totalLength; i++) {
        fullBuffer[i] = buffer[i % cycleLength];
    }

    // Generate filename
    const parts = generateFilenameParts();
    const filename = [
        parts.noteLetter,
        parts.waveform,
        parts.systemName,
        parts.levels,
        parts.subharmonicFlag
    ].filter(Boolean).join('-');

    // Generate WAV file
    const arrayBuffer = createWAVBuffer(fullBuffer, sampleRate);
    downloadWAVFile(arrayBuffer, filename);
    
    showStatus(`Wavetable exported as ${filename}.wav!`, 'success');
}

/**
 * Creates a WAV buffer from audio data
 * @param {Float32Array} buffer - Audio buffer
 * @param {number} sampleRate - Sample rate
 * @returns {ArrayBuffer} WAV file buffer
 */
function createWAVBuffer(buffer, sampleRate) {
    const bufferLen = buffer.length;
    const numOfChan = 1;
    const bytesPerSample = 2; // 16-bit
    const blockAlign = numOfChan * bytesPerSample;
    const byteRate = sampleRate * blockAlign;
    const dataSize = bufferLen * bytesPerSample;
    const fileSize = 36 + dataSize;
    
    const arrayBuffer = new ArrayBuffer(fileSize + 8);
    const view = new DataView(arrayBuffer);

    // Write RIFF chunk
    writeString(view, 0, 'RIFF');
    view.setUint32(4, fileSize, true); // Little-endian
    writeString(view, 8, 'WAVE');

    // Write FMT chunk
    writeString(view, 12, 'fmt ');
    view.setUint32(16, 16, true);          // Sub-chunk size
    view.setUint16(20, 1, true);           // PCM format
    view.setUint16(22, numOfChan, true);   // Mono
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, byteRate, true);
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, 16, true);          // 16 bits per sample

    // Write DATA chunk
    writeString(view, 36, 'data');
    view.setUint32(40, dataSize, true);

    // Write the actual audio data (converted to 16-bit integer)
    let offset = 44;
    for (let i = 0; i < bufferLen; i++, offset += 2) {
        const s = Math.max(-1, Math.min(1, buffer[i]));
        view.setInt16(offset, s * 0x7FFF, true);
    }

    return view;
}

/**
 * Writes a string to a DataView
 * @param {DataView} view - DataView to write to
 * @param {number} offset - Offset to write at
 * @param {string} string - String to write
 */
function writeString(view, offset, string) {
    for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
    }
}

/**
 * Downloads a WAV file
 * @param {DataView} arrayBuffer - WAV data
 * @param {string} filename - Filename without extension
 */
function downloadWAVFile(arrayBuffer, filename) {
    const blob = new Blob([arrayBuffer], { type: 'audio/wav' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${filename}.wav`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
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

    // Convert harmonic amplitudes to Fourier coefficients for PeriodicWave
    const numHarmonics = Math.min(AppState.harmonicAmplitudes.length, 128);
    const real = new Float32Array(numHarmonics + 1).fill(0);
    const imag = new Float32Array(numHarmonics + 1).fill(0);
    
    // Use the current harmonic amplitudes and ratios to build the Fourier series
    for (let h = 0; h < numHarmonics && h < AppState.harmonicAmplitudes.length; h++) {
        const amplitude = AppState.harmonicAmplitudes[h];
        const ratio = AppState.currentSystem.ratios[h];
        
        if (amplitude > 0 && ratio > 0) {
            // For each harmonic, find the closest integer harmonic
            const harmonicIndex = Math.round(ratio);
            if (harmonicIndex > 0 && harmonicIndex < real.length) {
                // Add to the sine component (imaginary) for the base waveform shape
                imag[harmonicIndex] += amplitude;
            }
        }
    }
    
    const customWave = AppState.audioContext.createPeriodicWave(real, imag, { disableNormalization: false });
    AppState.customWaveCount++;
    const waveKey = `custom_${AppState.customWaveCount}`;
    AppState.blWaveforms[waveKey] = customWave;

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
}