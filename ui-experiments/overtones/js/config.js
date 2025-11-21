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
        description:
            'Classic harmonic series (exact integer partials). Use for natural, consonant spectra (e.g. voiced instruments, organ-like timbres). See the harmonic-series background: <a href="https://en.wikipedia.org/wiki/Harmonic_series_(music)">Wikipedia — Harmonic series</a>.',
        // exact integer partials
        ratios: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        labelPrecision: 1
    },

    {
        name: "2. Spectral Progressive Detuned Harmonics (Microtonal)",
        description:
            'Progressive microtonal detuning of the integer harmonic series. detuning increases with partial index to produce time-varying beating and spectral shimmer (useful for spectral / ambient textures). This is an intentional synthesis choice rather than a canonical acoustic law.',
        // progressive detune: integer partials plus a small increasing offset (e.g. +0.01, +0.02, ...),
        // expressed as math to make the detune explicit.
        ratios: [
            1,
            2 + 0.01,         // 2.01 = 2 + 0.01
            3 + 0.02,         // 3.02
            4 + 0.03,         // 4.03
            5 + 0.04,         // 5.04
            6 + 0.05,         // 6.05
            7 + 0.06,         // 7.06
            8 + 0.08,         // 8.08
            9 + 0.10,         // 9.10
            10 + 0.12,        // 10.12
            11 + 0.14,        // 11.14
            12 + 0.16         // 12.16
        ],
        labelPrecision: 2
    },

    {
        name: "3. Inharmonic Membrane / Plate Modes (Bessel-root based)",
        description:
            'Modal ratios derived from the first zeros of Bessel-type modal functions — a physically informed inharmonic series used to synthesize metallic / bell / plate timbres. This is a simplified circular-membrane / plate approximation (modal zeros of Bessel functions scale the modal frequencies). For background, see the math of Bessel roots and plate/modal modeling: <a href="https://en.wikipedia.org/wiki/Bessel_function">Bessel functions</a> and a modal-plate overview: <a href="https://courses.cs.washington.edu/courses/cse481i/20wi/pdfs/G-waveguides.pdf">modal plate notes (UW)</a>.',
        // using the first several J0 zeros (approx): 2.404825557695773, 5.520078110286311, 8.653727912911013, 11.791534439014281...
        // ratios are normalized to the first root.
        ratios: [
            1,
            5.520078110286311 / 2.404825557695773,   // ≈ 2.2949
            8.653727912911013 / 2.404825557695773,   // ≈ 3.5994
            11.791534439014281 / 2.404825557695773,  // ≈ 4.9037
            14.930917708487787 / 2.404825557695773,  // ≈ 6.2079
            18.071063967910923 / 2.404825557695773,  // ≈ 7.5124
            21.21163662987926 / 2.404825557695773,  // ≈ 8.8167
            24.352471530749302 / 2.404825557695773,  // ≈ 10.1211
            27.493479132040254 / 2.404825557695773,  // ≈ 11.4254
            30.634606468431975 / 2.404825557695773,  // ≈ 12.7298
            33.77582021357357 / 2.404825557695773,  // ≈ 14.0340
            36.91709835366401 / 2.404825557695773   // ≈ 15.3384
        ],
        labelPrecision: 3
    },

    {
        name: "4. Gamelan Slendro (Common Approximation)",
        description:
            'A conservative Slendro approximation — Slendro tunings vary widely between ensembles and islands. This is a plausible normalized Slendro-like series (useful as a starting point). See tuning variability and research: <a href="https://eamusic.dartmouth.edu/~larry/misc_writings/out_of_print/slendro_balungan.pdf">Javanese Slendro analyses</a> and a detailed study: <a href="https://www.31edo.com/slendrogamelan.pdf">Stearns — Slendro analysis</a>.',
        // normalized values (progressing roughly between 1 and 2 over 5 steps, expanded here to 12 for spectral uses)
        ratios: [
            1,
            1.22,   // approx
            1.48,
            1.76,
            2.05,
            2.44,
            2.96,
            3.52,
            4.10,
            4.88,
            5.92,
            7.04
        ],
        labelPrecision: 2
    },

    {
        name: "4b. Slendro — Adventurous Variant (Exploratory)",
        description:
            'A more adventurous Slendro-inspired variant that shifts a few degrees towards septimal/7-limit alignments (useful for exotic spectral palettes). This is deliberately non-standard; treat it as a creative tuning palette rather than an ethnographic map.',
        ratios: [
            1,
            8 / 7,      // ~1.1429 — leaning toward septimal flavor
            7 / 5,      // 1.4
            12 / 7,     // ~1.714285...
            9 / 5,      // 1.8
            16 / 7,     // ~2.2857
            21 / 8,     // ~2.625
            7 / 2,      // 3.5
            9 / 2,
            11 / 2,
            13 / 2,
            15 / 2
        ],
        labelPrecision: 3
    },

    {
        name: "5. Gamelan Pelog (Common Approximation)",
        description:
            'A conservative Pelog approximation (Pelog also varies a lot by ensemble). This is a practical Pelog-like set for synthesis; it compresses Pelog’s characteristic unequal steps into a usable spectral array. See overview and sample tunings: <a href="https://tuning.ableton.com/sundanese-gamelan/">Ableton — Gamelan tuning intro</a>.',
        ratios: [
            1,
            1.06,
            1.25,
            1.33,
            1.5,
            1.66,
            1.78,
            2.0,
            2.12,
            2.5,
            2.66,
            3.0
        ],
        labelPrecision: 2
    },

    {
        name: "5b. Pelog — Adventurous Variant (Exploratory)",
        description:
            'A more adventurous Pelog variant that includes stronger septimal and odd-limit colors — useful when you want Pelog-ish contours but with richer microtonal tension.',
        ratios: [
            1,
            25 / 24,   // small upper chroma
            9 / 8,
            6 / 5,
            7 / 6,
            11 / 8,
            9 / 7,
            3 / 2,
            7 / 4,
            8 / 5,
            9 / 5,
            2
        ],
        labelPrecision: 3
    },

    {
        name: "6. Bohlen–Pierce (13-EDT of the Tritave)",
        description:
            'Equal-tempered Bohlen–Pierce: 13 equal divisions of the tritave (3:1) — the most common practical realization of BP. Each step = 3^(1/13) above the previous. Useful when you want the distinctive BP non-octave (tritave) periodicity. See the Bohlen–Pierce overview: <a href="https://en.wikipedia.org/wiki/Bohlen%E2%80%93Pierce_scale">Bohlen–Pierce (Wikipedia)</a>.',
        // math-style expressions for ET: 3^(n/13)
        ratios: [
            1,
            Math.pow(3, 1 / 13),
            Math.pow(3, 2 / 13),
            Math.pow(3, 3 / 13),
            Math.pow(3, 4 / 13),
            Math.pow(3, 5 / 13),
            Math.pow(3, 6 / 13),
            Math.pow(3, 7 / 13),
            Math.pow(3, 8 / 13),
            Math.pow(3, 9 / 13),
            Math.pow(3, 10 / 13),
            Math.pow(3, 11 / 13)
        ],
        labelPrecision: 3
    },

    {
        name: "6b. Bohlen–Pierce (Representative Just Intonation set)",
        description:
            'A commonly-cited Bohlen–Pierce just-intonation palette assembled from small-ratio JI intervals historically associated with BP discussions (normalized to 1). This is an illustrative JI BP set — there are multiple JI realizations in the literature. See the JI vs. ET BP table: <a href="https://en.wikipedia.org/wiki/Bohlen%E2%80%93Pierce_scale#Intervals_and_scale_diagrams">BP intervals (Wikipedia)</a>.',
        // representative JI ratios from BP literature, normalized to 1 (this list follows typical JI examples)
        ratios: [
            1,
            27 / 25,
            25 / 21,
            9 / 7,
            7 / 5,
            75 / 49,
            5 / 3,
            9 / 5,
            49 / 25,
            15 / 7,
            7 / 3,
            63 / 25
        ],
        labelPrecision: 3
    },

    {
        name: "7. Standardized Lydian Root Set (Just-intonation oriented)",
        description:
            'A compact, standardized Lydian root set expressed in just-intonation ratios. This keeps the Lydian #4 character while using small-integer ratios for musical stability — useful when you want a Lydian-centered just palette (informed by George Russellʼs idea of the Lydian center; see the Lydian Chromatic Concept: <a href="https://georgerussell.com/lydian-chromatic-concept">George Russell — Lydian Chromatic Concept</a>).',
        // 1 = tonic; 9/8 = major 2nd; 5/4 = major 3rd; raised 4th as 45/32 (a small-integer JI candidate near a #4)
        // then 3/2 (fifth), 8/5 (major sixth), 15/8 (major 7th approx). This is a compact JI Lydian-root set.
        ratios: [
            1,
            9 / 8,
            5 / 4,
            45 / 32,   // raised 4th (#4) as a plausible JI candidate
            3 / 2,
            8 / 5,
            15 / 8,
            2,
            9 / 4,
            5 / 2,
            15 / 4,
            4
        ],
        labelPrecision: 3
    },

    {
        name: "8. Fractional Series (n/4 Multiples)",
        description:
            'A deliberately inharmonic fractional series using n/4 multipliers (1, 1.25, 1.5, ...). Very metallic and clanging — excellent for bell-like additive synthesis with strong inharmonic beating.',
        ratios: [1, 5 / 4, 3 / 2, 7 / 4, 2, 9 / 4, 5 / 2, 11 / 4, 3, 13 / 4, 7 / 2, 15 / 4],
        labelPrecision: 2
    },

    // --- Harry Partch related sets (up to three) ---
    {
        name: "HP-A. Harry Partch — 43-Tone Scale (overview)",
        description:
            'Harry Partchʼs 43-tone scale (per octave) is a systematic 11-limit-based just-intonation framework Partch used for much of his instrument design and composition. It is not a simple scalar subset but a dense just lattice; this entry provides a practical normalization and pointers. See: <a href="https://en.wikipedia.org/wiki/Harry_Partch%27s_43-tone_scale">Harry Partchʼs 43-tone scale (Wikipedia)</a>.',
        // we won't list all 43 here inline; include a compact representative 12-value spectral subset sampled from Partch's 11-limit diamond
        ratios: [
            1,
            12 / 11,
            11 / 10,
            10 / 9,
            9 / 8,
            8 / 7,
            7 / 6,
            6 / 5,
            11 / 9,
            5 / 4,
            14 / 11,
            9 / 7
        ],
        labelPrecision: 4
    },

    {
        name: "HP-B. Harry Partch — 11-Limit Tonality Diamond (subset)",
        description:
            'A focused 11-limit tonality diamond subset (useful Partchian palette). This selection expresses Partchʼs hierarchy of consonance-to-dissonance in small integer ratios; use as a microtonal palette or for Partch-inspired composition. Reference: <a href="https://en.wikipedia.org/wiki/Harry_Partch%27s_43-tone_scale">Partch — 43-tone & 11-limit ideas</a>.',
        ratios: [
            1,
            16 / 15,
            9 / 8,
            6 / 5,
            5 / 4,
            4 / 3,
            7 / 5,
            3 / 2,
            8 / 5,
            5 / 3,
            9 / 5,
            2
        ],
        labelPrecision: 4
    },

    {
        name: "HP-C. Harry Partch — Practical Instrument Subset (for keyboard/percussion)",
        description:
            "A small practical subset inspired by the subsets Partch used on instruments (Chromelodeon, Adapted Guitar, etc.) — chosen for playability while retaining Partch's just-intonation character. See Partch instrument descriptions: <a href='https://en.wikipedia.org/wiki/Harry_Partch%27s_43-tone_scale'>Partch overview</a>.",
        ratios: [
            1,
            9 / 8,
            6 / 5,
            5 / 4,
            4 / 3,
            3 / 2,
            8 / 5,
            5 / 3,
            9 / 5,
            15 / 8,
            2,
            9 / 4
        ],
        labelPrecision: 4
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