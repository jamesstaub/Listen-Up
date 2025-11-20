/**
 * UTILITIES MODULE
 * Contains MIDI conversion, filename generation, and helper functions
 */

import { MIDI_NOTE_NAMES, AppState } from './config.js';

// ================================
// MIDI UTILITIES
// ================================

/**
 * Converts a MIDI note number to its corresponding frequency (Hz)
 * @param {number} midi - MIDI note number (0-127)
 * @returns {number} Frequency in Hz
 */
export function midiToFreq(midi) {
    return 440 * Math.pow(2, (midi - 69) / 12);
}

/**
 * Converts a frequency (Hz) to the closest MIDI note number
 * @param {number} frequency - Frequency in Hz
 * @returns {number} MIDI note number
 */
export function freqToMidi(frequency) {
    return 69 + 12 * Math.log2(frequency / 440);
}

/**
 * Converts a MIDI note number to its note name (e.g., 60 -> C4)
 * @param {number} midi - MIDI note number
 * @returns {string} Note name with octave
 */
export function midiToNoteName(midi) {
    const octave = Math.floor(midi / 12) - 1;
    const noteIndex = midi % 12;
    return MIDI_NOTE_NAMES[noteIndex] + octave;
}

// ================================
// FILENAME GENERATION
// ================================

/**
 * Converts a normalized gain value (0.0 to 1.0) into a single Base-16 character (0-F)
 * @param {number} gain - A float between 0.0 and 1.0
 * @returns {string} A single Hexadecimal character (0-F)
 */
function gainToHex(gain) {
    const level = Math.round(gain * 15);
    return level.toString(16).toUpperCase();
}

/**
 * Generates the 12-character compressed string representing the overtone levels
 * @returns {string} The compressed 12-character Base-16 string
 */
function generateOvertoneString() {
    return AppState.harmonicAmplitudes.slice(0, 12).map(gainToHex).join('');
}

/**
 * Gathers all state variables required for consistent filename/wave name structure
 * @returns {Object} Object containing filename parts
 */
export function generateFilenameParts() {
    const noteLetter = midiToNoteName(AppState.currentMidiNote).replace('#', 's');
    const waveform = AppState.currentWaveform.toUpperCase().replace('_', '-');
    const systemName = AppState.currentSystem.name.split('.')[1].trim().replace(/[^a-zA-Z0-9_]/g, '');
    const levels = generateOvertoneString();
    const subharmonicFlag = AppState.isSubharmonic ? 'subharmonic' : '';
    
    return {
        noteLetter,
        waveform,
        systemName,
        levels,
        subharmonicFlag
    };
}

// ================================
// FREQUENCY CALCULATIONS
// ================================

/**
 * Calculates the frequency based on the mode (Over/Sub-harmonic)
 * @param {number} ratio - The harmonic ratio
 * @returns {number} Calculated frequency in Hz
 */
export function calculateFrequency(ratio) {
    if (AppState.isSubharmonic) {
        return ratio === 0 ? 0 : AppState.fundamentalFrequency / ratio;
    } else {
        return AppState.fundamentalFrequency * ratio;
    }
}

// ================================
// STATUS MESSAGES
// ================================

/**
 * Shows a status message to the user
 * @param {string} message - Message to display
 * @param {string} type - Type of message ('info', 'success', 'warning', 'error')
 */
export function showStatus(message, type = 'info') {
    const statusBox = document.getElementById('status-message');
    if (!statusBox) return;
    
    statusBox.textContent = message;
    statusBox.classList.remove('hidden', 'error', 'success', 'warning', 'info');
    statusBox.classList.add(type);

    // Automatically hide after 4 seconds
    setTimeout(() => {
        statusBox.classList.add('hidden');
    }, 4000);
}

// ================================
// DOM UTILITIES
// ================================

/**
 * Safely gets an element by ID with error handling
 * @param {string} id - Element ID
 * @returns {Element|null} DOM element or null
 */
export function getElement(id) {
    const element = document.getElementById(id);
    if (!element) {
        console.warn(`Element with id '${id}' not found`);
    }
    return element;
}

/**
 * Sets up event listener with error handling
 * @param {string} elementId - Element ID
 * @param {string} event - Event type
 * @param {Function} handler - Event handler function
 */
export function setupEventListener(elementId, event, handler) {
    const element = getElement(elementId);
    if (element) {
        element.addEventListener(event, handler);
    }
}

/**
 * Updates an element's text content safely
 * @param {string} elementId - Element ID
 * @param {string} text - Text content to set
 */
export function updateText(elementId, text) {
    const element = getElement(elementId);
    if (element) {
        element.textContent = text;
    }
}

/**
 * Updates an element's value safely
 * @param {string} elementId - Element ID
 * @param {any} value - Value to set
 */
export function updateValue(elementId, value) {
    const element = getElement(elementId);
    if (element) {
        element.value = value;
    }
}

// ================================
// VALIDATION UTILITIES
// ================================

/**
 * Validates a frequency value
 * @param {number} frequency - Frequency to validate
 * @param {number} min - Minimum allowed value
 * @param {number} max - Maximum allowed value
 * @returns {boolean} Whether the frequency is valid
 */
export function validateFrequency(frequency, min = 10, max = 10000) {
    return !isNaN(frequency) && frequency >= min && frequency <= max;
}

/**
 * Clamps a value between min and max
 * @param {number} value - Value to clamp
 * @param {number} min - Minimum value
 * @param {number} max - Maximum value
 * @returns {number} Clamped value
 */
export function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
}

/**
 * Maps a value from one range to another
 * @param {number} value - Value to map
 * @param {number} start1 - Start of source range
 * @param {number} stop1 - End of source range
 * @param {number} start2 - Start of target range
 * @param {number} stop2 - End of target range
 * @returns {number} Mapped value
 */
export function mapRange(value, start1, stop1, start2, stop2) {
    return start2 + (stop2 - start2) * ((value - start1) / (stop1 - start1));
}

// ================================
// DEBOUNCING UTILITY
// ================================

/**
 * Creates a debounced version of a function
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Debounced function
 */
export function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}