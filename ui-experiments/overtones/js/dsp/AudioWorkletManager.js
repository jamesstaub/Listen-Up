/**
 * AUDIO WORKLET MANAGER
 * Manages AudioWorklet-based synthesis for better performance
 */

export class AudioWorkletManager {
    constructor(audioContext) {
        this.audioContext = audioContext;
        this.workletNode = null;
        this.isInitialized = false;
        this.isWorkletSupported = 'audioWorklet' in this.audioContext;
        
        // Track custom wavetables for copying to temporary nodes
        this.customWavetables = new Map();
        
        // Interpolation types available
        this.interpolationTypes = [
            { value: 'none', label: 'None (Nearest Neighbor)' },
            { value: 'linear', label: 'Linear' },
            { value: 'cubic', label: 'Cubic (Catmull-Rom)' },
            { value: 'quintic', label: 'Quintic (Smooth)' }
        ];
        
        // Output modes
        this.outputModes = [
            { value: 'mono', label: 'Mono Sum' },
            { value: 'multichannel', label: 'Per-Partial Channels' }
        ];
    }
    
    /**
     * Initialize the audio worklet
     */
    async initialize() {
        if (!this.isWorkletSupported) {
            throw new Error('AudioWorklet not supported in this browser');
        }
        
        try {
            // Load the worklet processor
            await this.audioContext.audioWorklet.addModule('./js/dsp/HarmonicSynthProcessor.js');
            
            // Create the worklet node with multiple output channels
            this.workletNode = new AudioWorkletNode(this.audioContext, 'harmonic-synth-processor', {
                numberOfInputs: 0,
                numberOfOutputs: 1,
                outputChannelCount: [32] // Support up to 32 output channels
            });
            
            // Set up error handling
            this.workletNode.onprocessorerror = (event) => {
                console.error('AudioWorklet processor error:', event);
            };
            
            // Initialize with sample rate
            this.sendMessage({
                type: 'setSampleRate',
                sampleRate: this.audioContext.sampleRate
            });
            
            this.isInitialized = true;
            
        } catch (error) {
            console.error('Failed to initialize AudioWorklet:', error);
            throw error;
        }
    }
    
    /**
     * Connect the worklet to the audio graph
     */
    connect(destination) {
        if (this.workletNode) {
            this.workletNode.connect(destination);
        }
    }
    
    /**
     * Disconnect the worklet
     */
    disconnect() {
        if (this.workletNode) {
            this.workletNode.disconnect();
        }
    }
    
    /**
     * Send message to worklet processor
     */
    sendMessage(data) {
        if (this.workletNode) {
            this.workletNode.port.postMessage(data);
        }
    }
    
    /**
     * Update fundamental frequency
     */
    updateFrequency(frequency) {
        this.currentFrequency = frequency;
        this.sendMessage({
            type: 'updateFrequency',
            frequency: frequency
        });
    }
    
    /**
     * Update harmonic amplitudes and ratios
     */
    updateHarmonics(amplitudes, ratios) {
        this.currentHarmonicAmplitudes = new Float32Array(amplitudes);
        this.currentHarmonicRatios = new Float32Array(ratios);
        this.sendMessage({
            type: 'updateHarmonics',
            amplitudes: Array.from(amplitudes),
            ratios: Array.from(ratios)
        });
    }
    
    /**
     * Update master gain
     */
    updateMasterGain(gain) {
        this.currentMasterGain = gain;
        this.sendMessage({
            type: 'updateMasterGain',
            gain: gain
        });
    }
    
    /**
     * Update current waveform
     */
    updateWaveform(waveform) {
        this.currentWaveform = waveform;
        this.sendMessage({
            type: 'updateWaveform',
            waveform: waveform
        });
    }
    
    /**
     * Set interpolation type
     */
    setInterpolationType(type) {
        const validTypes = this.interpolationTypes.map(t => t.value);
        if (!validTypes.includes(type)) {
            throw new Error(`Invalid interpolation type: ${type}`);
        }
        
        this.currentInterpolationType = type;
        this.sendMessage({
            type: 'setInterpolationType',
            interpolationType: type
        });
    }
    
    /**
     * Set output mode (mono or multichannel)
     */
    setOutputMode(mode) {
        const validModes = this.outputModes.map(m => m.value);
        if (!validModes.includes(mode)) {
            throw new Error(`Invalid output mode: ${mode}`);
        }
        
        this.sendMessage({
            type: 'setOutputMode',
            outputMode: mode
        });
    }
    
    /**
     * Reset phase for phase-locked synthesis
     */
    resetPhase() {
        this.sendMessage({
            type: 'resetPhase'
        });
    }
    
    /**
     * Add a custom wavetable
     */
    addWavetable(name, samples) {
        // Store locally for copying to temporary nodes
        this.customWavetables.set(name, new Float32Array(samples));
        
        // Send to main worklet node
        this.sendMessage({
            type: 'addWavetable',
            name: name,
            samples: Array.from(samples)
        });
    }
    
    /**
     * Copy all custom wavetables to a temporary worklet node
     * Essential for recursive waveform building where custom waveforms are sampled
     */
    copyWavetablesToTempNode(tempWorkletNode) {
        for (const [name, samples] of this.customWavetables) {
            tempWorkletNode.port.postMessage({
                type: 'addWavetable',
                name: name,
                samples: Array.from(samples)
            });
        }
    }
    
    /**
     * Get available interpolation types
     */
    getInterpolationTypes() {
        return [...this.interpolationTypes];
    }
    
    /**
     * Get available output modes
     */
    getOutputModes() {
        return [...this.outputModes];
    }
    
    /**
     * Check if worklets are supported
     */
    isSupported() {
        return this.isWorkletSupported;
    }
    
    /**
     * Sample the current waveform output for wavetable creation
     * This captures the actual synthesized output, preserving the current waveform
     */
    async sampleCurrentOutput(sampleLength = 2048) {
        if (!this.isReady()) {
            throw new Error('AudioWorkletManager not initialized');
        }
        
        return new Promise((resolve, reject) => {
            // Create an offline context for clean sampling
            const offlineContext = new OfflineAudioContext(1, sampleLength, this.audioContext.sampleRate);
            
            // Create a temporary worklet node in the offline context
            offlineContext.audioWorklet.addModule('./js/dsp/HarmonicSynthProcessor.js')
                .then(() => {
                    const tempWorkletNode = new AudioWorkletNode(offlineContext, 'harmonic-synth-processor');
                    
                    // Copy all custom wavetables to temp worklet (CRITICAL for recursive waveform building)
                    this.copyWavetablesToTempNode(tempWorkletNode);
                    
                    // Copy current parameters to temp worklet
                    tempWorkletNode.port.postMessage({
                        type: 'updateHarmonics',
                        amplitudes: this.currentHarmonicAmplitudes || new Float32Array(32),
                        ratios: this.currentHarmonicRatios || new Float32Array(32)
                    });
                    
                    tempWorkletNode.port.postMessage({
                        type: 'updateFrequency',
                        frequency: this.currentFrequency || 220
                    });
                    
                    tempWorkletNode.port.postMessage({
                        type: 'updateWaveform',
                        waveform: this.currentWaveform || 'sine'
                    });
                    
                    tempWorkletNode.port.postMessage({
                        type: 'updateMasterGain',
                        gain: 1.0
                    });
                    
                    tempWorkletNode.port.postMessage({
                        type: 'setInterpolationType',
                        interpolationType: this.currentInterpolationType || 'linear'
                    });
                    
                    tempWorkletNode.port.postMessage({
                        type: 'resetPhase'
                    });
                    
                    // Connect to output and render
                    tempWorkletNode.connect(offlineContext.destination);
                    
                    offlineContext.startRendering()
                        .then(buffer => {
                            // Extract one cycle worth of samples
                            const samples = buffer.getChannelData(0);
                            const cycleLength = Math.min(sampleLength, samples.length);
                            const result = new Float32Array(cycleLength);
                            
                            // Copy samples
                            for (let i = 0; i < cycleLength; i++) {
                                result[i] = samples[i];
                            }
                            
                            // Normalize
                            let maxAmplitude = 0;
                            for (let i = 0; i < cycleLength; i++) {
                                maxAmplitude = Math.max(maxAmplitude, Math.abs(result[i]));
                            }
                            
                            if (maxAmplitude > 0) {
                                const normalizationFactor = 1.0 / maxAmplitude;
                                for (let i = 0; i < cycleLength; i++) {
                                    result[i] *= normalizationFactor;
                                }
                            }
                            
                            resolve(result);
                        })
                        .catch(reject);
                })
                .catch(reject);
        });
    }
    
    /**
     * Store current parameters for sampling purposes
     */
    storeCurrentParameters(harmonicAmplitudes, harmonicRatios, frequency, waveform, interpolationType) {
        this.currentHarmonicAmplitudes = harmonicAmplitudes;
        this.currentHarmonicRatios = harmonicRatios;
        this.currentFrequency = frequency;
        this.currentWaveform = waveform;
        this.currentInterpolationType = interpolationType;
    }
    
    /**
     * Check if initialized
     */
    isReady() {
        return this.isInitialized && this.workletNode;
    }
    
    /**
     * Get the worklet node for advanced routing
     */
    getWorkletNode() {
        return this.workletNode;
    }
    
    /**
     * Cleanup
     */
    dispose() {
        if (this.workletNode) {
            this.workletNode.disconnect();
            this.workletNode = null;
        }
        this.isInitialized = false;
    }
}