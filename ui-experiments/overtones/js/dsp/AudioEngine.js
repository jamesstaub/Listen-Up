/**
 * AUDIO ENGINE CLASS
 * Manages Web Audio API context and oscillator graph with optional AudioWorklet support
 */

import { WaveformGenerator } from './WaveformGenerator.js';
import { AudioWorkletManager } from './AudioWorkletManager.js';

export class AudioEngine {
    constructor() {
        this.context = null;
        this.masterGain = null;
        this.compressor = null;
        this.oscillators = new Map();
        this.isInitialized = false;
        
        // AudioWorklet support
        this.workletManager = null;
        this.useAudioWorklet = false;
        this.workletMode = 'mono'; // 'mono' or 'multichannel'
        this.interpolationType = 'linear';
        
        // Standard waveforms
        this.standardWaveforms = new Map();
    }
    
    /**
     * Initializes the audio engine
     * @param {number} masterGainValue - Initial master gain value
     * @param {Object} options - Configuration options
     */
    async initialize(masterGainValue = 0.3, options = {}) {
        if (this.isInitialized) return;
        
        // Create audio context
        this.context = new (window.AudioContext || window.webkitAudioContext)();
        
        // Set up AudioWorklet if requested and supported
        if (options.useAudioWorklet !== false) {
            try {
                this.workletManager = new AudioWorkletManager(this.context);
                if (this.workletManager.isSupported()) {
                    await this.workletManager.initialize();
                    this.useAudioWorklet = true;
                    console.log('AudioWorklet initialized successfully');
                }
            } catch (error) {
                console.warn('AudioWorklet initialization failed, falling back to oscillators:', error);
                this.useAudioWorklet = false;
            }
        }
        
        // Create audio graph
        this.setupAudioGraph(masterGainValue);
        
        // Pre-generate standard waveforms (for oscillator fallback)
        this.generateStandardWaveforms();
        
        // Connect AudioWorklet if available
        if (this.useAudioWorklet && this.workletManager) {
            this.workletManager.connect(this.compressor);
            this.workletManager.setInterpolationType(this.interpolationType);
            this.workletManager.setOutputMode(this.workletMode);
        }
        
        this.isInitialized = true;
        
        // Resume context if suspended
        if (this.context.state === 'suspended') {
            await this.context.resume();
        }
    }
    
    /**
     * Sets up the main audio processing graph
     * @param {number} masterGainValue - Initial master gain value
     */
    setupAudioGraph(masterGainValue) {
        // Create dynamics compressor
        this.compressor = this.context.createDynamicsCompressor();
        this.compressor.threshold.setValueAtTime(-12, this.context.currentTime);
        this.compressor.ratio.setValueAtTime(12, this.context.currentTime);

        // Create master gain node
        this.masterGain = this.context.createGain();
        this.masterGain.gain.setValueAtTime(masterGainValue, this.context.currentTime);
        this.masterGain.maxGain = 1.0;

        // Connect the audio graph
        this.compressor.connect(this.masterGain);
        this.masterGain.connect(this.context.destination);
    }
    
    /**
     * Generates standard band-limited waveforms
     */
    generateStandardWaveforms() {
        const types = ['square', 'sawtooth', 'triangle'];
        
        for (const type of types) {
            const periodicWave = WaveformGenerator.createBandLimitedWaveform(this.context, type);
            this.standardWaveforms.set(type, periodicWave);
        }
    }
    
    /**
     * Start synthesis using the appropriate method (AudioWorklet or oscillators)
     */
    startSynthesis(harmonicAmplitudes, harmonicRatios, fundamentalFreq, waveform) {
        if (this.useAudioWorklet && this.workletManager) {
            return this.startWorkletSynthesis(harmonicAmplitudes, harmonicRatios, fundamentalFreq, waveform);
        } else {
            return this.startOscillatorSynthesis(harmonicAmplitudes, harmonicRatios, fundamentalFreq, waveform);
        }
    }
    
    /**
     * Stop synthesis
     */
    stopSynthesis() {
        if (this.useAudioWorklet && this.workletManager) {
            // Reset amplitudes to zero for worklet
            const zeroAmplitudes = new Float32Array(32).fill(0);
            const zeroRatios = new Float32Array(32).fill(0);
            this.workletManager.updateHarmonics(zeroAmplitudes, zeroRatios);
        } else {
            this.stopAllOscillators();
        }
    }
    
    /**
     * Update synthesis parameters
     */
    updateSynthesis(harmonicAmplitudes, harmonicRatios, fundamentalFreq, masterGain) {
        if (this.useAudioWorklet && this.workletManager) {
            this.workletManager.updateHarmonics(harmonicAmplitudes, harmonicRatios);
            this.workletManager.updateFrequency(fundamentalFreq);
            this.workletManager.updateMasterGain(masterGain);
        } else {
            // Update individual oscillators
            this.updateOscillatorParameters(harmonicAmplitudes, harmonicRatios, fundamentalFreq, masterGain);
        }
    }
    
    /**
     * Set interpolation type for AudioWorklet
     */
    setInterpolationType(type) {
        this.interpolationType = type;
        if (this.useAudioWorklet && this.workletManager) {
            this.workletManager.setInterpolationType(type);
        }
    }
    
    /**
     * Set output mode (mono or multichannel)
     */
    setOutputMode(mode) {
        this.workletMode = mode;
        if (this.useAudioWorklet && this.workletManager) {
            this.workletManager.setOutputMode(mode);
        }
    }
    
    /**
     * Reset phase for phase-locked synthesis
     */
    resetPhase() {
        if (this.useAudioWorklet && this.workletManager) {
            this.workletManager.resetPhase();
        }
        // Note: Oscillator-based synthesis doesn't support phase reset
    }
    
    /**
     * Add custom waveform
     */
    addCustomWaveform(name, samples) {
        if (this.useAudioWorklet && this.workletManager) {
            this.workletManager.addWavetable(name, samples);
        }
        // For oscillator fallback, waveforms are handled via PeriodicWave
    }
    
    /**
     * Sample current waveform output for wavetable creation
     * Uses AudioWorklet sampling if available for accurate capture
     */
    async sampleCurrentWaveform(sampleLength = 2048) {
        if (this.useAudioWorklet && this.workletManager) {
            try {
                return await this.workletManager.sampleCurrentOutput(sampleLength);
            } catch (error) {
                console.warn('AudioWorklet sampling failed, falling back to basic sampling:', error);
                // Fall through to basic sampling
            }
        }
        
        // Fallback to basic harmonic synthesis sampling
        // This would be implemented for oscillator-based synthesis
        throw new Error('Basic sampling not yet implemented for oscillator fallback');
    }
    
    /**
     * Get available interpolation types
     */
    getInterpolationTypes() {
        if (this.workletManager) {
            return this.workletManager.getInterpolationTypes();
        }
        return [{ value: 'linear', label: 'Linear (Oscillator Mode)' }];
    }
    
    /**
     * Get available output modes
     */
    getOutputModes() {
        if (this.workletManager) {
            return this.workletManager.getOutputModes();
        }
        return [{ value: 'mono', label: 'Mono (Oscillator Mode)' }];
    }
    
    /**
     * Check if using AudioWorklet
     */
    isUsingAudioWorklet() {
        return this.useAudioWorklet;
    }
    
    /**
     * Start AudioWorklet synthesis
     */
    startWorkletSynthesis(harmonicAmplitudes, harmonicRatios, fundamentalFreq, waveform) {
        if (!this.workletManager) {
            return false;
        }
        
        this.workletManager.updateHarmonics(harmonicAmplitudes, harmonicRatios);
        this.workletManager.updateFrequency(fundamentalFreq);
        this.workletManager.updateWaveform(waveform);
        this.workletManager.updateMasterGain(1.0); // Ensure master gain is set
        this.workletManager.resetPhase(); // Ensure phase-locked start
        
        return true;
    }
    
    /**
     * Start oscillator-based synthesis (fallback)
     */
    startOscillatorSynthesis(harmonicAmplitudes, harmonicRatios, fundamentalFreq, waveform) {
        // Clear any existing oscillators
        this.stopAllOscillators();
        
        // Create oscillators for each harmonic
        for (let i = 0; i < harmonicAmplitudes.length; i++) {
            const amplitude = harmonicAmplitudes[i];
            const ratio = harmonicRatios[i];
            
            if (amplitude > 0 && ratio > 0) {
                const frequency = fundamentalFreq * ratio;
                const gain = amplitude;
                
                try {
                    // Create and start oscillator
                    const oscData = this.createOscillator(frequency, waveform, gain);
                    const oscKey = `harmonic_${i}`;
                    this.addOscillator(oscKey, oscData);
                } catch (error) {
                    console.error(`Failed to create oscillator ${i}:`, error);
                }
            }
        }
        
        return true;
    }
    
    /**
     * Update oscillator parameters (for fallback mode)
     */
    updateOscillatorParameters(harmonicAmplitudes, harmonicRatios, fundamentalFreq, masterGain) {
        // Implementation for updating individual oscillators
        // This would be similar to existing updateOscillatorFrequency/Gain methods
    }

    /**
     * Creates a new oscillator with the specified configuration
     * @param {number} frequency - Oscillator frequency in Hz
     * @param {string|PeriodicWave} waveform - Waveform type or custom PeriodicWave
     * @param {number} gain - Oscillator gain (0-1)
     * @returns {Object} Object containing oscillator and gain nodes
     */
    createOscillator(frequency, waveform, gain = 1.0) {
        if (!this.isInitialized) {
            throw new Error("AudioEngine must be initialized before creating oscillators");
        }
        
        const oscillator = this.context.createOscillator();
        const gainNode = this.context.createGain();
        
        // Set frequency
        oscillator.frequency.setValueAtTime(frequency, this.context.currentTime);
        
        // Set waveform
        if (typeof waveform === 'string') {
            if (waveform === 'sine') {
                oscillator.type = 'sine';
            } else if (this.standardWaveforms.has(waveform)) {
                oscillator.setPeriodicWave(this.standardWaveforms.get(waveform));
            } else {
                throw new Error(`Unknown waveform type: ${waveform}`);
            }
        } else if (waveform instanceof PeriodicWave) {
            oscillator.setPeriodicWave(waveform);
        } else {
            throw new Error("Waveform must be a string or PeriodicWave");
        }
        
        // Set gain
        gainNode.gain.setValueAtTime(gain, this.context.currentTime);
        
        // Connect nodes
        oscillator.connect(gainNode);
        gainNode.connect(this.compressor);
        
        return { oscillator, gainNode };
    }
    
    /**
     * Adds an oscillator to the active oscillators map
     * @param {string} key - Unique key for the oscillator
     * @param {Object} oscData - Oscillator data from createOscillator
     */
    addOscillator(key, oscData) {
        this.oscillators.set(key, oscData);
        oscData.oscillator.start();
    }
    
    /**
     * Removes and stops an oscillator
     * @param {string} key - Oscillator key
     */
    removeOscillator(key) {
        const oscData = this.oscillators.get(key);
        if (oscData) {
            oscData.oscillator.stop();
            oscData.oscillator.disconnect();
            oscData.gainNode.disconnect();
            this.oscillators.delete(key);
        }
    }
    
    /**
     * Stops and removes all oscillators
     */
    stopAllOscillators() {
        for (const [key, oscData] of this.oscillators) {
            oscData.oscillator.stop();
            oscData.oscillator.disconnect();
            oscData.gainNode.disconnect();
        }
        this.oscillators.clear();
    }
    
    /**
     * Updates an oscillator's frequency with exponential ramping
     * @param {string} key - Oscillator key
     * @param {number} frequency - New frequency
     * @param {number} rampTime - Ramp time in seconds
     */
    updateOscillatorFrequency(key, frequency, rampTime = 0.05) {
        const oscData = this.oscillators.get(key);
        if (oscData) {
            const now = this.context.currentTime;
            oscData.oscillator.frequency.exponentialRampToValueAtTime(frequency, now + rampTime);
        }
    }
    
    /**
     * Updates an oscillator's gain with exponential ramping
     * @param {string} key - Oscillator key  
     * @param {number} gain - New gain value
     * @param {number} rampTime - Ramp time in seconds
     */
    updateOscillatorGain(key, gain, rampTime = 0.05) {
        const oscData = this.oscillators.get(key);
        if (oscData) {
            const now = this.context.currentTime;
            // Allow true zero gain for silence
            if (gain <= 0) {
                oscData.gainNode.gain.setValueAtTime(0, now);
            } else {
                oscData.gainNode.gain.exponentialRampToValueAtTime(gain, now + rampTime);
            }
        }
    }
    
    /**
     * Updates master gain with exponential ramping
     * @param {number} gain - New master gain value
     * @param {number} rampTime - Ramp time in seconds
     */
    updateMasterGain(gain, rampTime = 0.05) {
        if (this.masterGain) {
            const now = this.context.currentTime;
            const clampedGain = Math.min(gain, this.masterGain.maxGain);
            // Allow true zero gain for silence
            if (clampedGain <= 0) {
                this.masterGain.gain.setValueAtTime(0, now);
            } else {
                this.masterGain.gain.exponentialRampToValueAtTime(clampedGain, now + rampTime);
            }
        }
    }
    
    /**
     * Gets the audio context
     * @returns {AudioContext} The audio context
     */
    getContext() {
        return this.context;
    }
    
    /**
     * Gets a standard waveform PeriodicWave
     * @param {string} type - Waveform type
     * @returns {PeriodicWave|null} The PeriodicWave or null if not found
     */
    getStandardWaveform(type) {
        return this.standardWaveforms.get(type) || null;
    }
    
    /**
     * Cleanup and disconnect all audio nodes
     */
    dispose() {
        this.stopAllOscillators();
        
        if (this.masterGainNode) {
            this.masterGainNode.disconnect();
        }
        
        if (this.compressor) {
            this.compressor.disconnect();
        }
        
        if (this.workletManager) {
            this.workletManager.dispose();
        }
        
        this.isInitialized = false;
    }
    
    /**
     * Get current configuration and status
     */
    getStatus() {
        return {
            initialized: this.isInitialized,
            usingAudioWorklet: this.useAudioWorklet,
            interpolationType: this.interpolationType,
            outputMode: this.workletMode,
            activeOscillators: this.oscillators.size,
            sampleRate: this.context ? this.context.sampleRate : null,
            state: this.context ? this.context.state : null
        };
    }
    
    /**
     * Handle AudioWorklet initialization errors gracefully
     */
    handleWorkletError(error) {
        console.warn('AudioWorklet initialization failed, falling back to oscillators:', error);
        this.useAudioWorklet = false;
        this.workletManager = null;
        // You could emit an event here to notify the UI
    }
    
    /**
     * Checks if the engine is initialized
     * @returns {boolean} True if initialized
     */
    isReady() {
        return this.isInitialized && this.context && this.context.state === 'running';
    }
    
    /**
     * Resumes the audio context if suspended
     */
    resume() {
        if (this.context && this.context.state === 'suspended') {
            return this.context.resume();
        }
        return Promise.resolve();
    }
}

export default AudioEngine;