/**
 * HARMONIC SYNTHESIS AUDIO WORKLET PROCESSOR
 * Real-time harmonic series synthesis with custom waveforms and interpolation
 */

class HarmonicSynthProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        
        // Synthesis parameters
        this.fundamentalFreq = 220;
        this.harmonicAmplitudes = new Float32Array(32).fill(0);
        this.harmonicRatios = new Float32Array(32).fill(0);
        this.masterGain = 0.3;
        this.currentWaveform = 'sine';
        
        // Interpolation settings
        this.interpolationType = 'linear'; // 'none', 'linear', 'cubic', 'quintic'
        
        // Phase-locked synthesis
        this.fundamentalPhase = 0;
        this.isPhaseReset = false;
        
        // Wavetable storage
        this.wavetables = new Map();
        this.wavetableSize = 2048;
        
        // Sample rate
        this.sampleRate = 44100;
        
        // Output mode
        this.outputMode = 'mono'; // 'mono', 'multichannel'
        this.maxChannels = 32;
        
        // Listen for parameter updates from main thread
        this.port.onmessage = (event) => {
            this.handleMessage(event.data);
        };
        
        // Initialize with sine wavetable
        this.generateSineWavetable();
        this.generateStandardWavetables();
    }
    
    /**
     * Main audio processing function
     */
    process(inputs, outputs, parameters) {
        const output = outputs[0];
        
        if (!output || output.length === 0) return true;
        
        const blockSize = output[0].length;
        const numChannels = this.outputMode === 'multichannel' ? 
            Math.min(output.length, this.maxChannels) : Math.min(output.length, 2); // Ensure stereo in mono mode
        
        // Clear all output channels
        for (let ch = 0; ch < numChannels; ch++) {
            if (output[ch]) {
                output[ch].fill(0);
            }
        }
        
        // Calculate phase increment for fundamental
        const fundamentalPhaseIncrement = (this.fundamentalFreq * 2 * Math.PI) / this.sampleRate;
        
        // Reset phases if requested (for phase-locked synthesis)
        if (this.isPhaseReset) {
            this.fundamentalPhase = 0;
            this.isPhaseReset = false;
        }
        
        // Generate each harmonic
        for (let h = 0; h < this.harmonicAmplitudes.length; h++) {
            const amplitude = this.harmonicAmplitudes[h];
            const ratio = this.harmonicRatios[h];
            
            if (amplitude > 0 && ratio > 0) {
                // Skip frequencies above Nyquist to prevent aliasing
                const harmonicFreq = this.fundamentalFreq * ratio;
                if (harmonicFreq >= this.sampleRate / 2) {
                    continue;
                }
                
                const targetChannel = this.outputMode === 'multichannel' ? 
                    Math.min(h, numChannels - 1) : 0;
                
                if (!output[targetChannel]) continue;
                
                for (let i = 0; i < blockSize; i++) {
                    // Phase-locked harmonic phase calculation with better precision
                    const samplePhase = this.fundamentalPhase + (i * fundamentalPhaseIncrement);
                    const harmonicPhase = (samplePhase * ratio) % (2 * Math.PI);
                    
                    // Get waveform sample with interpolation
                    const sample = this.getWaveformSample(this.currentWaveform, harmonicPhase);
                    
                    // Apply amplitude and add to output
                    const outputSample = sample * amplitude * this.masterGain;
                    output[targetChannel][i] += outputSample;
                    
                    // In mono mode, also output to right channel for stereo
                    if (this.outputMode === 'mono' && output[1] && targetChannel === 0) {
                        output[1][i] += outputSample;
                    }
                }
            }
        }
        
        // Update fundamental phase for next block
        this.fundamentalPhase += fundamentalPhaseIncrement * blockSize;
        this.fundamentalPhase = this.fundamentalPhase % (2 * Math.PI);
        
        // Apply soft clipping to prevent harsh distortion
        for (let ch = 0; ch < numChannels; ch++) {
            if (output[ch]) {
                for (let i = 0; i < blockSize; i++) {
                    output[ch][i] = Math.tanh(output[ch][i]);
                }
            }
        }
        
        return true;
    }
    
    /**
     * Get waveform sample at given phase with interpolation
     */
    getWaveformSample(waveform, phase) {
        if (waveform === 'sine') {
            return Math.sin(phase);
        }
        
        // Use wavetable lookup for custom waveforms
        if (this.wavetables.has(waveform)) {
            return this.interpolateWavetable(this.wavetables.get(waveform), phase);
        }
        
        // Fallback to sine
        return Math.sin(phase);
    }
    
    /**
     * Interpolate wavetable sample with configurable interpolation
     */
    interpolateWavetable(table, phase) {
        const normalizedPhase = (phase % (2 * Math.PI)) / (2 * Math.PI);
        const index = normalizedPhase * (table.length - 1);
        
        switch (this.interpolationType) {
            case 'none':
                return table[Math.round(index)] || 0;
                
            case 'linear':
                return this.linearInterpolate(table, index);
                
            case 'cubic':
                return this.cubicInterpolate(table, index);
                
            case 'quintic':
                return this.quinticInterpolate(table, index);
                
            default:
                return this.linearInterpolate(table, index);
        }
    }
    
    /**
     * Linear interpolation
     */
    linearInterpolate(table, index) {
        const lowIndex = Math.floor(index);
        const highIndex = (lowIndex + 1) % table.length;
        const fraction = index - lowIndex;
        
        return table[lowIndex] * (1 - fraction) + table[highIndex] * fraction;
    }
    
    /**
     * Cubic interpolation (Catmull-Rom)
     */
    cubicInterpolate(table, index) {
        const i1 = Math.floor(index);
        const i0 = (i1 - 1 + table.length) % table.length;
        const i2 = (i1 + 1) % table.length;
        const i3 = (i1 + 2) % table.length;
        const t = index - i1;
        
        const v0 = table[i0];
        const v1 = table[i1];
        const v2 = table[i2];
        const v3 = table[i3];
        
        return v1 + 0.5 * t * (
            v2 - v0 + t * (
                2 * v0 - 5 * v1 + 4 * v2 - v3 + t * (
                    3 * (v1 - v2) + v3 - v0
                )
            )
        );
    }
    
    /**
     * Quintic interpolation (smoother)
     */
    quinticInterpolate(table, index) {
        const i1 = Math.floor(index);
        const i0 = (i1 - 1 + table.length) % table.length;
        const i2 = (i1 + 1) % table.length;
        const t = index - i1;
        
        // Quintic smoothstep
        const smoothT = t * t * t * (t * (t * 6 - 15) + 10);
        
        return table[i1] * (1 - smoothT) + table[i2] * smoothT;
    }
    
    /**
     * Generate sine wavetable
     */
    generateSineWavetable() {
        const table = new Float32Array(this.wavetableSize);
        for (let i = 0; i < this.wavetableSize; i++) {
            const phase = (i / this.wavetableSize) * 2 * Math.PI;
            table[i] = Math.sin(phase);
        }
        this.wavetables.set('sine', table);
    }
    
    /**
     * Generate standard waveform wavetables
     */
    generateStandardWavetables() {
        // Square wave
        const square = new Float32Array(this.wavetableSize);
        for (let i = 0; i < this.wavetableSize; i++) {
            const phase = (i / this.wavetableSize) * 2 * Math.PI;
            square[i] = phase < Math.PI ? 1 : -1;
        }
        this.wavetables.set('square', square);
        
        // Sawtooth wave
        const sawtooth = new Float32Array(this.wavetableSize);
        for (let i = 0; i < this.wavetableSize; i++) {
            sawtooth[i] = (2 * i / this.wavetableSize) - 1;
        }
        this.wavetables.set('sawtooth', sawtooth);
        
        // Triangle wave
        const triangle = new Float32Array(this.wavetableSize);
        for (let i = 0; i < this.wavetableSize; i++) {
            const t = i / this.wavetableSize;
            triangle[i] = t < 0.5 ? (4 * t - 1) : (3 - 4 * t);
        }
        this.wavetables.set('triangle', triangle);
    }
    
    /**
     * Handle messages from main thread
     */
    handleMessage(data) {
        switch (data.type) {
            case 'updateFrequency':
                this.fundamentalFreq = data.frequency;
                break;
                
            case 'updateHarmonics':
                if (data.amplitudes) {
                    this.harmonicAmplitudes.set(data.amplitudes);
                }
                if (data.ratios) {
                    this.harmonicRatios.set(data.ratios);
                }
                break;
                
            case 'updateMasterGain':
                this.masterGain = data.gain;
                break;
                
            case 'updateWaveform':
                this.currentWaveform = data.waveform;
                break;
                
            case 'setInterpolationType':
                this.interpolationType = data.interpolationType;
                break;
                
            case 'setOutputMode':
                this.outputMode = data.outputMode;
                break;
                
            case 'resetPhase':
                this.isPhaseReset = true;
                break;
                
            case 'addWavetable':
                this.wavetables.set(data.name, new Float32Array(data.samples));
                break;
                
            case 'setSampleRate':
                this.sampleRate = data.sampleRate;
                break;
                
            default:
                console.warn('Unknown message type:', data.type);
        }
    }
}

// Register the processor
registerProcessor('harmonic-synth-processor', HarmonicSynthProcessor);