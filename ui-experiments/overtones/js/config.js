/**
 * CONFIGURATION MODULE
 * Contains spectral systems, constants, and application state
 */

// ================================
// SPECTRAL SYSTEMS CONFIGURATION
// ================================

export const spectralSystems = [
    {
        name: "1. Harmonic Overtone Series (Integer)",
        description: "The natural integer multiples (1x, 2x, 3x...) found in Western instruments. Creates consonant, classic timbres.",
        ratios: [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0],
        labelPrecision: 1 
    },
    {
        name: "2. Spectral Detuned Harmonics (Microtonal)",
        description: "Ratios are slightly detuned (microtonal) from integer values. This creates complex beating and psychoacoustic shimmer, popular in spectral music.",
        ratios: [1.0, 2.01, 2.99, 4.05, 5.0, 6.02, 7.0, 8.03, 8.98, 10.04, 11.0, 12.01],
        labelPrecision: 2 
    },
    {
        name: "3. Inharmonic Bell (Simplified Ratios)",
        description: "Approximated ratios based on a stiff vibrating plate or bell ($f \\propto n^2$). These non-integer multiples create metallic, ringing, and dissonant textures.",
        ratios: [1.0, 2.8, 5.2, 8.0, 11.5, 15.6, 20.3, 25.6, 31.5, 38.0, 45.1, 52.8], 
        labelPrecision: 1 
    },
    {
        name: "4. Gamelan Slendro Approximation",
        description: "Approximated frequency ratios based on the five-tone, non-equally spaced Slendro scale of Indonesian Gamelan. Highly unique, non-Western melodic intervals.",
        ratios: [1.0, 1.22, 1.48, 1.76, 2.05, 2.44, 2.96, 3.52, 4.10, 4.88, 5.92, 7.04],
        labelPrecision: 2 
    },
    {
        name: "5. Gamelan Pelog Approximation",
        description: "Seven-tone Indonesian Gamelan (Pelog) approximated. Features wider and less symmetrical intervals than Slendro, leading to rich, dark timbres.",
        ratios: [1.0, 1.06, 1.25, 1.33, 1.5, 1.66, 1.78, 2.0, 2.12, 2.5, 2.66, 3.0],
        labelPrecision: 2 
    },
    {
        name: "6. Bohlen-Pierce Ratios (Tritave 3:1)",
        description: "A famous Xenharmonic scale where the 'octave' is replaced by the tritave (3:1). Sounds unusual as the 2nd partial is highly dissonant (2.25x).",
        ratios: [1.0, 1.07, 1.15, 1.25, 1.35, 1.5, 1.6, 1.7, 1.84, 2.0, 2.15, 2.3],
        labelPrecision: 2 
    },
    {
        name: "7. High-Ratio Lydian (Russell Concept)",
        description: "A non-traditional harmonic context favoring the Lydian mode, using higher integer-based ratios often associated with natural acoustic resonance.",
        ratios: [1.0, 1.125, 1.266, 1.333, 1.406, 1.5, 1.687, 1.777, 1.875, 2.0, 2.11, 2.25],
        labelPrecision: 3 
    },
    {
        name: "8. Fractional Series ($n/4$ Multiples)",
        description: "A highly inharmonic series built on $n/4$ multipliers (1.0, 1.25, 1.5, 1.75...). Creates a metallic, clanging, and extremely dissonant spectrum.",
        ratios: [1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 3.25, 3.5, 3.75],
        labelPrecision: 2 
    }
];

// ================================
// CONSTANTS
// ================================

export const MIDI_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];

export const DEFAULT_FUNDAMENTAL = 130.81; // C3
export const DEFAULT_MIDI_NOTE = 48; // MIDI for C3
export const DEFAULT_OCTAVE = 3;
export const BASE_OCTAVE_MIDI = 48; // MIDI for C3

export const WAVETABLE_SIZE = 4096; // Standard size for a PeriodicWave table
export const NUM_HARMONICS = 12;
export const DEFAULT_MASTER_GAIN = 0.03;

// Visualization constants
export const VISUAL_HARMONIC_TERMS = 7;
export const CANVAS_HEIGHT_RATIOS = {
    RADIAL: 0.75,
    OSCILLOSCOPE: 0.25
};

export const HARMONIC_COLORS = [
    '#10b981', '#fcd34d', '#3b82f6', '#ef4444', 
    '#a855f7', '#f97316', '#22c55e', '#ec4899',
    '#84cc16', '#eab308', '#7c3aed', '#6d28d9'
];

export const DRAWBAR_STYLES = [
    'white', 'brown', 'white', 'white', 'brown', 'black', 
    'brown', 'white', 'black', 'blue', 'red', 'black'
];

// ================================
// APPLICATION STATE
// ================================

export const AppState = {
    // Audio properties
    masterGainValue: DEFAULT_MASTER_GAIN,
    fundamentalFrequency: DEFAULT_FUNDAMENTAL,
    currentMidiNote: DEFAULT_MIDI_NOTE,
    currentOctave: DEFAULT_OCTAVE,
    isPlaying: false,
    
    // Spectral properties
    currentSystem: spectralSystems[0],
    harmonicAmplitudes: (() => {
        const amplitudes = Array(NUM_HARMONICS).fill(0.0);
        amplitudes[0] = 1.0; // Fundamental enabled by default
        return amplitudes;
    })(),
    isSubharmonic: false,
    currentWaveform: 'sine',
    
    // Visualization properties
    visualizationFrequency: 2.0,
    spreadFactor: 0.2,
    
    // Custom waveforms
    customWaveCount: 0,
    
    // Audio context references (initialized later)
    audioContext: null,
    compressor: null,
    masterGain: null,
    oscillators: [],
    blWaveforms: {}, // Band-limited waveforms
    
    // P5 instance reference
    p5Instance: null
};

// ================================
// STATE MANAGEMENT
// ================================

export function updateAppState(updates) {
    Object.assign(AppState, updates);
}

export function resetHarmonicAmplitudes() {
    AppState.harmonicAmplitudes.fill(0.0);
    AppState.harmonicAmplitudes[0] = 1.0;
}

export function getCurrentSystem() {
    return AppState.currentSystem;
}

export function setCurrentSystem(systemIndex) {
    AppState.currentSystem = spectralSystems[systemIndex];
}

export function getHarmonicAmplitude(index) {
    return AppState.harmonicAmplitudes[index] || 0;
}

export function setHarmonicAmplitude(index, amplitude) {
    if (index >= 0 && index < AppState.harmonicAmplitudes.length) {
        AppState.harmonicAmplitudes[index] = amplitude;
    }
}