/**
 * WAVETABLE MANAGER CLASS
 * Manages custom waveforms, their coefficients, and storage
 */

import { DFT } from './DFT.js';
import { WaveformGenerator } from './WaveformGenerator.js';

export class WavetableManager {
    constructor() {
        this.waveforms = new Map();
        this.coefficients = new Map();
        this.periodMultipliers = new Map(); // Store period multipliers for pitch correction
        this.count = 0;
    }
    
    /**
     * Adds a new custom waveform from time-domain samples
     * @param {Float32Array} samples - Time-domain samples
     * @param {AudioContext} context - Web Audio context
     * @param {number} maxHarmonics - Maximum harmonics to analyze
     * @param {number} periodMultiplier - Period multiplier for pitch correction
     * @returns {string} Unique key for the new waveform
     */
    addFromSamples(samples, context, maxHarmonics = 128, periodMultiplier = 1) {
        if (samples.length === 0) {
            throw new Error("Cannot add empty waveform data.");
        }
        
        // Perform DFT to extract frequency components
        const { real, imag } = DFT.transform(samples, maxHarmonics);
        
        // Create PeriodicWave
        const periodicWave = WaveformGenerator.createCustomWaveform(context, real, imag);
        
        // Generate unique key
        this.count++;
        const key = `custom_${this.count}`;
        
        // Store waveform, coefficients, and period multiplier
        this.waveforms.set(key, periodicWave);
        this.coefficients.set(key, { real, imag });
        this.periodMultipliers.set(key, periodMultiplier);
        
        return key;
    }
    
    /**
     * Adds a new custom waveform from Fourier coefficients
     * @param {Float32Array} real - Real coefficients
     * @param {Float32Array} imag - Imaginary coefficients
     * @param {AudioContext} context - Web Audio context
     * @returns {string} Unique key for the new waveform
     */
    addFromCoefficients(real, imag, context) {
        const periodicWave = WaveformGenerator.createCustomWaveform(context, real, imag);
        
        this.count++;
        const key = `custom_${this.count}`;
        
        this.waveforms.set(key, periodicWave);
        this.coefficients.set(key, { 
            real: new Float32Array(real), 
            imag: new Float32Array(imag) 
        });
        
        return key;
    }
    
    /**
     * Gets a stored PeriodicWave
     * @param {string} key - Waveform key
     * @returns {PeriodicWave|null} The PeriodicWave or null if not found
     */
    getWaveform(key) {
        return this.waveforms.get(key) || null;
    }
    
    /**
     * Gets stored Fourier coefficients
     * @param {string} key - Waveform key
     * @returns {Object|null} Object with real and imag arrays, or null if not found
     */
    getCoefficients(key) {
        return this.coefficients.get(key) || null;
    }
    
    /**
     * Gets the period multiplier for pitch correction
     * @param {string} key - Waveform key
     * @returns {number} Period multiplier (1 if not found)
     */
    getPeriodMultiplier(key) {
        return this.periodMultipliers.get(key) || 1;
    }
    
    /**
     * Reconstructs time-domain samples from stored coefficients
     * @param {string} key - Waveform key
     * @param {number} sampleCount - Number of samples to generate
     * @returns {Float32Array|null} Time-domain samples or null if not found
     */
    reconstructSamples(key, sampleCount = 512) {
        const coeffs = this.coefficients.get(key);
        if (!coeffs) return null;
        
        return DFT.inverseTransform(coeffs.real, coeffs.imag, sampleCount);
    }
    
    /**
     * Gets all stored waveform keys
     * @returns {Array<string>} Array of waveform keys
     */
    getAllKeys() {
        return Array.from(this.waveforms.keys());
    }
    
    /**
     * Removes a stored waveform
     * @param {string} key - Waveform key to remove
     * @returns {boolean} True if removed, false if not found
     */
    remove(key) {
        const hadWaveform = this.waveforms.delete(key);
        const hadCoefficients = this.coefficients.delete(key);
        return hadWaveform && hadCoefficients;
    }
    
    /**
     * Clears all stored waveforms
     */
    clear() {
        this.waveforms.clear();
        this.coefficients.clear();
        this.count = 0;
    }
    
    /**
     * Gets the current count of stored waveforms
     * @returns {number} Number of stored waveforms
     */
    getCount() {
        return this.waveforms.size;
    }
    
    /**
     * Exports waveform data for serialization
     * @param {string} key - Waveform key
     * @returns {Object|null} Serializable waveform data or null if not found
     */
    exportData(key) {
        const coeffs = this.coefficients.get(key);
        if (!coeffs) return null;
        
        return {
            key,
            real: Array.from(coeffs.real),
            imag: Array.from(coeffs.imag),
            timestamp: Date.now()
        };
    }
    
    /**
     * Imports waveform data from serialization
     * @param {Object} data - Serialized waveform data
     * @param {AudioContext} context - Web Audio context
     * @returns {string} The imported waveform key
     */
    importData(data, context) {
        const real = new Float32Array(data.real);
        const imag = new Float32Array(data.imag);
        
        return this.addFromCoefficients(real, imag, context);
    }
}