// UIStateManager.js
// Centralizes state update logic for fundamental, drawbars, etc. Used by keyboard, MIDI, and UI modules.

import { AppState, updateAppState, spectralSystems } from './config.js';
import { updateFundamentalDisplay, updateKeyboardUI } from './ui.js';
import { updateAudioProperties } from './audio.js';

export class UIStateManager {
    // Set fundamental by MIDI note
    static setFundamentalByMidi(midiNote) {
        const midi = Math.min(127, midiNote); // Clamp upper bound
        const frequency = UIStateManager.midiToFreq(midi);
        const octave = Math.floor(midi / 12) - 1;
        updateAppState({
            currentMidiNote: midi,
            fundamentalFrequency: frequency,
            currentOctave: octave
        });
        updateFundamentalDisplay();
        updateKeyboardUI();
        updateAudioProperties();
    }

    // Set fundamental by frequency
    static setFundamentalByFrequency(freq) {
        const midi = Math.round(UIStateManager.freqToMidi(freq));
        UIStateManager.setFundamentalByMidi(midi);
    }

    // Set drawbar gain by index
    static setDrawbarGain(index, value) {
        const amps = AppState.harmonicAmplitudes;
        if (amps && amps.length > index) {
            amps[index] = value;
            updateAppState({ harmonicAmplitudes: amps });
            updateAudioProperties();
        }
    }

    // Utility: MIDI <-> Frequency
    static midiToFreq(midi) {
        return 440 * Math.pow(2, (midi - 69) / 12);
    }
    static freqToMidi(freq) {
        return 69 + 12 * Math.log2(freq / 440);
    }
}
