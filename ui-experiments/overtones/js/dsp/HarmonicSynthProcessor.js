/**
 * HARMONIC SYNTHESIS AUDIO WORKLET PROCESSOR
 * Real-time harmonic series synthesis with custom waveforms
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
        
        // Wavetable storage
        this.wavetables = new Map();
        this.wavetableSize = 2048;
        
        // Phase accumulators for each harmonic
        this.phases = new Float32Array(32).fill(0);
        
        // Sample rate
        this.sampleRate = 44100;
        
        // Listen for parameter updates from main thread
        this.port.onmessage = (event) => {
            this.handleMessage(event.data);
        };
        
        // Initialize with sine wavetable
        this.generateSineWavetable();
    }
    
    /**
     * Main audio processing function
     */
    process(inputs, outputs, parameters) {
        const output = outputs[0];
        const outputChannel = output[0];
        
        if (!outputChannel) return true;
        
        const blockSize = outputChannel.length;
        
        // Clear output buffer
        outputChannel.fill(0);
        
        // Generate each harmonic
        for (let h = 0; h < this.harmonicAmplitudes.length; h++) {
            const amplitude = this.harmonicAmplitudes[h];
            const ratio = this.harmonicRatios[h];
            
            if (amplitude > 0 && ratio > 0) {
                const frequency = this.fundamentalFreq * ratio;
                const phaseIncrement = (frequency * 2 * Math.PI) / this.sampleRate;
                
                for (let i = 0; i < blockSize; i++) {
                    // Get waveform sample
                    const sample = this.getWaveformSample(this.currentWaveform, this.phases[h]);
                    
                    // Apply amplitude and add to output
                    outputChannel[i] += sample * amplitude * this.masterGain;
                    
                    // Update phase
                    this.phases[h] += phaseIncrement;
                    if (this.phases[h] >= 2 * Math.PI) {
                        this.phases[h] -= 2 * Math.PI;
                    }
                }
            }
        }
        
        // Soft clipping to prevent harsh distortion
        for (let i = 0; i < blockSize; i++) {
            outputChannel[i] = Math.tanh(outputChannel[i]);
        }
        
        return true;
    }
    
    /**
     * Get waveform sample at given phase
     */
    getWaveformSample(waveform, phase) {
        if (waveform === 'sine') {
            return Math.sin(phase);
        }
        
        // Use wavetable lookup for custom waveforms
        if (this.wavetables.has(waveform)) {
            const table = this.wavetables.get(waveform);
            const normalizedPhase = phase / (2 * Math.PI);
            const index = normalizedPhase * (table.length - 1);
            const lowIndex = Math.floor(index);
            const highIndex = Math.ceil(index);
            const fraction = index - lowIndex;
            
            if (lowIndex === highIndex) {
                return table[lowIndex];
            } else {
                return table[lowIndex] * (1 - fraction) + table[highIndex] * fraction;
            }
        }
        
        // Fallback to sine
        return Math.sin(phase);
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