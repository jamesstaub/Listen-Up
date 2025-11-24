// initUI.js
// Initializes all modules and wires up event handlers
import { KeyboardShortcuts } from './KeyboardShortcuts.js';
import { DrawbarControls } from './DrawbarControls.js';
import { FundamentalControls } from './FundamentalControls.js';
import { HelpDialog } from './HelpDialog.js';

export function initUI() {
    // Main UI event handlers (drawbars, fundamental, help)
    document.getElementById('randomize-drawbars-button')?.addEventListener('click', DrawbarControls.randomizeDrawbars);
    document.getElementById('reset-drawbars-button')?.addEventListener('click', DrawbarControls.resetDrawbars);
    HelpDialog.init();
    // Keyboard shortcuts
    const kb = new KeyboardShortcuts();
    kb.init();
    // Fundamental controls (octave, note selection) can be wired as needed
    window.changeOctave = FundamentalControls.changeOctave;
}
