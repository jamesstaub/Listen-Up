/**
 * UI MODULE
 * Contains UI event handlers, DOM manipulation, and interface logic
 */

import { 
    AppState, 
    updateAppState, 
    spectralSystems, 
    setCurrentSystem, 
    setHarmonicAmplitude,
    DRAWBAR_STYLES,
    MIDI_NOTE_NAMES
} from './config.js';
import { 
    midiToFreq, 
    freqToMidi, 
    midiToNoteName, 
    validateFrequency,
    setupEventListener,
    updateText,
    updateValue,
    showStatus,
    smoothUpdateHarmonicAmplitude,
    smoothUpdateMasterGain,
    smoothUpdateSystem,
    smoothUpdateSubharmonicMode
} from './utils.js';
import { startTone, stopTone, updateAudioProperties, restartAudio, sampleCurrentWaveform, exportAsWAV, addToWaveforms } from './audio.js';
import { setSpreadFactor } from './visualization.js';

// ================================
// INITIALIZATION
// ================================

/**
 * Initializes all UI components and event handlers
 */
export function initUI() {
    setupMainButtons();
    setupControlSliders();
    setupFundamentalControls();
    setupKeyboard();
    setupSystemSelector();
    setupSubharmonicToggle();
    setupWaveformSelector();
    setupDrawbars();
    
    // Set initial UI values
    updateFundamentalDisplay();
    updateKeyboardUI();
    populateSystemSelector();
    updateDrawbarLabels();
    updateSystemDescription();
}

// ================================
// MAIN CONTROL BUTTONS
// ================================

function setupMainButtons() {
    // Play/Stop button
    setupEventListener('play-button', 'click', handlePlayToggle);
    
    // Export WAV button
    setupEventListener('export-wav-button', 'click', handleExportWAV);
    
    // Add to waveforms button
    setupEventListener('add-wave-button', 'click', handleAddToWaveforms);
}

function handlePlayToggle() {
    const button = document.getElementById('play-button');
    if (AppState.isPlaying) {
        stopTone();
        button.textContent = "Start Tone";
        button.classList.remove('playing');
    } else {
        startTone();
        button.textContent = "Stop Tone";
        button.classList.add('playing');
    }
}

function handleExportWAV() {
    const sampledBuffer = sampleCurrentWaveform();
    if (sampledBuffer.length > 0) {
        exportAsWAV(sampledBuffer, 1);
    }
}

function handleAddToWaveforms() {
    const sampledBuffer = sampleCurrentWaveform();
    if (sampledBuffer.length > 0) {
        addToWaveforms(sampledBuffer);
    }
}

// ================================
// CONTROL SLIDERS
// ================================

function setupControlSliders() {
    // Master gain slider
    const masterGainSlider = document.getElementById('master-gain-slider');
    const masterGainDisplay = document.getElementById('master-gain-value');
    
    if (masterGainSlider) {
        masterGainSlider.addEventListener('input', (e) => {
            const value = parseFloat(e.target.value);
            updateText('master-gain-value', `${(value * 100).toFixed(0)}%`);
            
            // Use smooth parameter interpolation to prevent crackling
            smoothUpdateMasterGain(value);
        });
    }

    // Spread slider
    const spreadSlider = document.getElementById('spread-slider');
    const spreadDisplay = document.getElementById('spread-value');
    
    if (spreadSlider) {
        spreadSlider.addEventListener('input', (e) => {
            const value = parseFloat(e.target.value);
            setSpreadFactor(value);
            updateText('spread-value', `${(value * 100).toFixed(0)}%`);
        });
    }

    // Visualization frequency slider
    const vizFreqSlider = document.getElementById('viz-freq-slider');
    const vizFreqDisplay = document.getElementById('viz-freq-value');
    
    if (vizFreqSlider) {
        vizFreqSlider.addEventListener('input', (e) => {
            const value = parseFloat(e.target.value);
            updateAppState({ visualizationFrequency: value });
            updateText('viz-freq-value', `${value.toFixed(1)} Hz`);
        });
    }
}

// ================================
// FUNDAMENTAL FREQUENCY CONTROLS
// ================================

function setupFundamentalControls() {
    // Frequency input
    const fundamentalInput = document.getElementById('fundamental-input');
    if (fundamentalInput) {
        fundamentalInput.addEventListener('change', handleFundamentalChange);
    }

    // Octave controls
    setupEventListener('octave-down', 'click', () => changeOctave(-1));
    setupEventListener('octave-up', 'click', () => changeOctave(1));
}

function handleFundamentalChange(e) {
    let val = parseFloat(e.target.value);
    if (!validateFrequency(val)) {
        showStatus("Frequency must be between 10 Hz and 10000 Hz.", 'error');
        val = AppState.fundamentalFrequency; // Revert to current value
    }
    
    updateAppState({ fundamentalFrequency: val });
    e.target.value = val.toFixed(2);
    
    // Update MIDI note and keyboard selection
    const newMidiNote = Math.round(freqToMidi(val));
    const newOctave = Math.floor(newMidiNote / 12) - 1;
    
    updateAppState({ 
        currentMidiNote: newMidiNote,
        currentOctave: newOctave 
    });
    
    updateKeyboardUI();
    updateAudioProperties();
}

function changeOctave(direction) {
    
    const newMidiNote = AppState.currentMidiNote + (direction * 12);
    updateFundamental(newMidiNote);
}

function updateFundamental(newMidi) {
    const clampedMidi = Math.max(0, Math.min(127, newMidi));
    const frequency = midiToFreq(clampedMidi);
    const octave = Math.floor(clampedMidi / 12) - 1;
    
    updateAppState({
        currentMidiNote: clampedMidi,
        fundamentalFrequency: frequency,
        currentOctave: octave
    });
    
    updateFundamentalDisplay();
    updateKeyboardUI();
    updateAudioProperties();
}

function updateFundamentalDisplay() {
    updateValue('fundamental-input', AppState.fundamentalFrequency.toFixed(2));
    updateText('current-octave-display', `Octave ${AppState.currentOctave}`);
}

// ================================
// KEYBOARD INTERFACE
// ================================

function setupKeyboard() {
    const keyboard = document.getElementById('piano-keyboard');
    if (!keyboard) return;

    // Define the 12 chromatic notes
    const notes = [
        { name: 'C', class: 'white', index: 0 },
        { name: 'C#', class: 'black', index: 1 },
        { name: 'D', class: 'white', index: 2 },
        { name: 'D#', class: 'black', index: 3 },
        { name: 'E', class: 'white', index: 4 },
        { name: 'F', class: 'white', index: 5 },
        { name: 'F#', class: 'black', index: 6 },
        { name: 'G', class: 'white', index: 7 },
        { name: 'G#', class: 'black', index: 8 },
        { name: 'A', class: 'white', index: 9 },
        { name: 'A#', class: 'black', index: 10 },
        { name: 'B', class: 'white', index: 11 },
    ];

    keyboard.innerHTML = ''; // Clear existing keys

    notes.forEach(note => {
        const key = document.createElement('div');
        key.className = `key ${note.class}`;
        key.textContent = note.name;
        key.dataset.noteIndex = note.index;
        key.addEventListener('click', () => handleKeyClick(note.index));
        keyboard.appendChild(key);
    });
}

function handleKeyClick(noteIndex) {
    // noteIndex is 0 (C) through 11 (B)
    const baseMidi = (AppState.currentOctave + 1) * 12;
    const newMidi = baseMidi + noteIndex;
    updateFundamental(newMidi);
}

function updateKeyboardUI() {
    const keys = document.querySelectorAll('.key');
    keys.forEach(key => key.classList.remove('active'));

    // Calculate the index (0-11) of the selected note within the current octave
    const noteIndex = AppState.currentMidiNote % 12;
    const selectedKey = document.querySelector(`.key[data-note-index="${noteIndex}"]`);
    
    if (selectedKey) {
        selectedKey.classList.add('active');
    }
}

// ================================
// SYSTEM SELECTOR
// ================================

function setupSystemSelector() {
    const select = document.getElementById('ratio-system-select');
    if (select) {
        select.addEventListener('change', handleSystemChange);
    }
}

function populateSystemSelector() {
    const select = document.getElementById('ratio-system-select');
    if (!select) return;

    select.innerHTML = ''; // Clear existing options

    spectralSystems.forEach((system, index) => {
        const option = document.createElement('option');
        option.textContent = system.name;
        option.value = index;
        select.appendChild(option);
    });
}

function handleSystemChange(e) {
    const systemIndex = parseInt(e.target.value);
    
    // Use smooth system update with UI update callback
    smoothUpdateSystem(systemIndex, () => {
        // Update UI after the system state has actually changed
        updateDrawbarLabels();
        updateSystemDescription();
    });
}

function updateSystemDescription() {
    updateText('system-description', AppState.currentSystem.description);
}

// ================================
// SUBHARMONIC TOGGLE
// ================================

function setupSubharmonicToggle() {
    const toggle = document.getElementById('subharmonic-toggle');
    if (toggle) {
        toggle.addEventListener('click', handleSubharmonicToggle);
    }
}

function handleSubharmonicToggle() {
    const isSubharmonic = !AppState.isSubharmonic;
    
    // Update immediate UI elements first
    const toggle = document.getElementById('subharmonic-toggle');
    const subharmonicLabel = document.getElementById('subharmonic-label');
    const overtoneLabel = toggle?.previousElementSibling;
    
    if (toggle) {
        toggle.classList.toggle('active', isSubharmonic);
        toggle.setAttribute('aria-checked', isSubharmonic);
    }

    // Update label colors
    if (subharmonicLabel && overtoneLabel) {
        if (isSubharmonic) {
            subharmonicLabel.classList.add('active');
            subharmonicLabel.classList.remove('inactive');
            overtoneLabel.classList.remove('overtone');
            overtoneLabel.classList.add('inactive');
        } else {
            subharmonicLabel.classList.remove('active');
            subharmonicLabel.classList.add('inactive');
            overtoneLabel.classList.add('overtone');
            overtoneLabel.classList.remove('inactive');
        }
    }
    
    // Use smooth mode update with callback for UI updates that depend on state
    smoothUpdateSubharmonicMode(isSubharmonic, () => {
        // Update drawbar labels after the state has actually changed
        updateDrawbarLabels();
    });
}

// ================================
// WAVEFORM SELECTOR
// ================================

function setupWaveformSelector() {
    const select = document.getElementById('waveform-select');
    if (select) {
        select.addEventListener('change', handleWaveformChange);
    }
}

function handleWaveformChange(e) {
    updateAppState({ currentWaveform: e.target.value });
    if (AppState.isPlaying) {
        restartAudio();
    }
}

// ================================
// DRAWBARS
// ================================

function setupDrawbars() {
    const container = document.getElementById('drawbars');
    if (!container) return;

    container.innerHTML = ''; // Clear existing drawbars

    for (let i = 0; i < AppState.harmonicAmplitudes.length; i++) {
        const drawbar = createDrawbar(i);
        container.appendChild(drawbar);
    }
}

function createDrawbar(index) {
    const styleClass = DRAWBAR_STYLES[index];
    const initialValue = AppState.harmonicAmplitudes[index];

    const drawbarDiv = document.createElement('div');
    drawbarDiv.className = `drawbar ${styleClass}`;
    
    const labelSpan = document.createElement('span');
    labelSpan.className = 'drawbar-label';
    labelSpan.id = `drawbar-label-${index}`;
    
    const inputWrapper = document.createElement('div');
    inputWrapper.className = 'drawbar-input-wrapper';
    
    const trackDiv = document.createElement('div');
    trackDiv.className = 'drawbar-track';
    
    const input = document.createElement('input');
    input.type = 'range';
    input.className = 'drawbar-slider';
    input.min = '0';
    input.max = '1';
    input.step = '0.01';
    input.value = initialValue;
    input.dataset.index = index;
    
    input.addEventListener('input', handleDrawbarChange);

    inputWrapper.appendChild(trackDiv);
    inputWrapper.appendChild(input);
    drawbarDiv.appendChild(labelSpan);
    drawbarDiv.appendChild(inputWrapper);
    
    return drawbarDiv;
}

function handleDrawbarChange(e) {
    const index = parseInt(e.target.dataset.index);
    const value = parseFloat(e.target.value);
    
    // Use smooth parameter interpolation to prevent crackling
    smoothUpdateHarmonicAmplitude(index, value);
}

function updateDrawbarLabels() {
    AppState.currentSystem.ratios.forEach((ratio, index) => {
        const labelElement = document.getElementById(`drawbar-label-${index}`);
        if (labelElement) {
            const preciseRatio = ratio.toFixed(AppState.currentSystem.labelPrecision);
            const labelText = AppState.isSubharmonic ? `1/${preciseRatio}x` : `${preciseRatio}x`;
            labelElement.textContent = labelText;
        }
    });
}

// ================================
// UI UPDATE FUNCTIONS
// ================================

/**
 * Updates all UI elements to reflect current state
 */
export function updateUI() {
    updateFundamentalDisplay();
    updateKeyboardUI();
    updateDrawbarLabels();
    updateSystemDescription();
    
    // Update slider values
    updateValue('master-gain-slider', AppState.masterGainValue);
    updateText('master-gain-value', `${(AppState.masterGainValue * 100).toFixed(0)}%`);
    
    updateValue('viz-freq-slider', AppState.visualizationFrequency);
    updateText('viz-freq-value', `${AppState.visualizationFrequency.toFixed(1)} Hz`);
    
    // Update play button state
    const playButton = document.getElementById('play-button');
    if (playButton) {
        playButton.textContent = AppState.isPlaying ? "Stop Tone" : "Start Tone";
        playButton.classList.toggle('playing', AppState.isPlaying);
    }
    
    // Update system selector
    const systemSelect = document.getElementById('ratio-system-select');
    if (systemSelect) {
        const systemIndex = spectralSystems.indexOf(AppState.currentSystem);
        systemSelect.value = systemIndex;
    }
    
    // Update waveform selector
    updateValue('waveform-select', AppState.currentWaveform);
    
    // Update subharmonic toggle
    const toggle = document.getElementById('subharmonic-toggle');
    if (toggle) {
        toggle.classList.toggle('active', AppState.isSubharmonic);
        toggle.setAttribute('aria-checked', AppState.isSubharmonic);
    }
}

// ================================
// ACCESSIBILITY HELPERS
// ================================

/**
 * Sets up keyboard shortcuts and accessibility features
 */
export function setupAccessibility() {
    document.addEventListener('keydown', (e) => {
        // Space bar to toggle play/pause
        if (e.code === 'Space' && e.target.tagName !== 'INPUT') {
            e.preventDefault();
            handlePlayToggle();
        }
        
        // Arrow keys for octave navigation
        if (e.code === 'ArrowUp' && e.ctrlKey) {
            e.preventDefault();
            changeOctave(1);
        }
        if (e.code === 'ArrowDown' && e.ctrlKey) {
            e.preventDefault();
            changeOctave(-1);
        }
    });
}