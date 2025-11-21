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
            
            // Create the worklet node
            this.workletNode = new AudioWorkletNode(this.audioContext, 'harmonic-synth-processor');
            
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
        this.sendMessage({
            type: 'updateFrequency',
            frequency: frequency
        });
    }
    
    /**
     * Update harmonic amplitudes and ratios
     */
    updateHarmonics(amplitudes, ratios) {
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
        this.sendMessage({
            type: 'updateMasterGain',
            gain: gain
        });
    }
    
    /**
     * Update current waveform
     */
    updateWaveform(waveform) {
        this.sendMessage({
            type: 'updateWaveform',
            waveform: waveform
        });
    }
    
    /**
     * Add a custom wavetable
     */
    addWavetable(name, samples) {
        this.sendMessage({
            type: 'addWavetable',
            name: name,
            samples: Array.from(samples)
        });
    }
    
    /**
     * Check if worklets are supported
     */
    isSupported() {
        return this.isWorkletSupported;
    }
    
    /**
     * Check if initialized
     */
    isReady() {
        return this.isInitialized && this.workletNode;
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