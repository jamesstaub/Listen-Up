// KeyboardShortcuts.js
// Handles all keyboard event mapping, calls UIStateManager methods

import { UIStateManager } from './UIStateManager.js';

export class KeyboardShortcuts {
    constructor() {
        this.focusedDrawbar = null;
    }

    init() {
        document.addEventListener('keydown', (e) => {
            // Spacebar: Play/Stop (handled elsewhere)
            if (e.code === 'Space') {
                e.preventDefault();
                document.getElementById('play-toggle')?.click();
                return;
            }
            // QWERTY row: Fundamental note selection
            const qwertyKeys = ['KeyA','KeyS','KeyD','KeyF','KeyG','KeyH','KeyJ','KeyK','KeyL','Semicolon','Quote','Backslash'];
            const qwertyIndex = qwertyKeys.indexOf(e.code);
            if (qwertyIndex !== -1) {
                const baseMidi = (window.AppState.currentOctave + 1) * 12;
                UIStateManager.setFundamentalByMidi(baseMidi + qwertyIndex);
                return;
            }
            // Number row: Drawbar focus
            const drawbarKeys = ['Digit1','Digit2','Digit3','Digit4','Digit5','Digit6','Digit7','Digit8','Digit9','Digit0','Minus','Equal'];
            const drawbarIndex = drawbarKeys.indexOf(e.code);
            if (drawbarIndex !== -1) {
                const drawbars = document.querySelectorAll('#drawbars .drawbar-slider');
                if (drawbars[drawbarIndex]) {
                    drawbars[drawbarIndex].focus();
                    this.focusedDrawbar = drawbars[drawbarIndex];
                }
                return;
            }
            // Arrow keys for drawbar gain control
            if (this.focusedDrawbar) {
                if (e.code === 'ArrowUp') {
                    e.preventDefault();
                    let val = e.shiftKey ? 1 : Math.min(1, parseFloat(this.focusedDrawbar.value) + 0.01);
                    this.focusedDrawbar.value = val.toFixed(2);
                    UIStateManager.setDrawbarGain(parseInt(this.focusedDrawbar.dataset.index), val);
                    this.focusedDrawbar.dispatchEvent(new Event('input', { bubbles: true }));
                    return;
                }
                if (e.code === 'ArrowDown') {
                    e.preventDefault();
                    let val = e.shiftKey ? 0 : Math.max(0, parseFloat(this.focusedDrawbar.value) - 0.01);
                    this.focusedDrawbar.value = val.toFixed(2);
                    UIStateManager.setDrawbarGain(parseInt(this.focusedDrawbar.dataset.index), val);
                    this.focusedDrawbar.dispatchEvent(new Event('input', { bubbles: true }));
                    return;
                }
            }
            // Ctrl+ArrowUp/Down: Octave navigation
            if (e.code === 'ArrowUp' && e.ctrlKey) {
                e.preventDefault();
                window.changeOctave?.(1);
                return;
            }
            if (e.code === 'ArrowDown' && e.ctrlKey) {
                e.preventDefault();
                window.changeOctave?.(-1);
                return;
            }
        });
    }
}
