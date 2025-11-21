/**
 * AUDIO ENGINE CLASS
 * Manages Web Audio API context and oscillator graph
 */

import { WaveformGenerator } from './WaveformGenerator.js';

export class AudioEngine {
    constructor() {
        this.context = null;
        this.masterGain = null;
        this.compressor = null;
        this.oscillators = new Map();
        this.isInitialized = false;
        
        // Standard waveforms
        this.standardWaveforms = new Map();
    }
    
    /**
     * Initializes the audio engine
     * @param {number} masterGainValue - Initial master gain value
     */
    initialize(masterGainValue = 0.3) {
        if (this.isInitialized) return;
        
        // Create audio context
        this.context = new (window.AudioContext || window.webkitAudioContext)();
        
        // Create audio graph
        this.setupAudioGraph(masterGainValue);
        
        // Pre-generate standard waveforms
        this.generateStandardWaveforms();
        
        this.isInitialized = true;
        
        // Resume context if suspended
        if (this.context.state === 'suspended') {
            this.context.resume();
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
            const targetGain = Math.max(0.001, gain); // Avoid zero for exponential ramp
            oscData.gainNode.gain.exponentialRampToValueAtTime(targetGain, now + rampTime);
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
            const targetGain = Math.max(0.001, Math.min(gain, this.masterGain.maxGain));
            this.masterGain.gain.exponentialRampToValueAtTime(targetGain, now + rampTime);
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