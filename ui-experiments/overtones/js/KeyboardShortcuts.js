// KeyboardShortcuts.js
// Handles all keyboard event mapping, calls UIStateManager methods

import { DrawbarsActions } from './modules/drawbars/drawbarsActions.js';
import { UIStateManager } from './UIStateManager.js';
import { handlePlayToggle } from './ui.js';

export class KeyboardShortcuts {
    constructor() {
        this.focusedDrawbar = null;
    }

    init() {
        document.addEventListener('keydown', (e) => {
            // Always allow spacebar to toggle play/stop
            if (e.code === 'Space') {
                e.preventDefault();
                handlePlayToggle();
                return
            }

            // QWERTY row: Fundamental note selection
            const qwertyKeys = ['KeyA','KeyS','KeyD','KeyF','KeyG','KeyH','KeyJ','KeyK','KeyL','Semicolon','Quote','Backslash'];
            const qwertyIndex = qwertyKeys.indexOf(e.code);
            if (qwertyIndex !== -1) {
                const state = UIStateManager.getState();
                const baseMidi = ((state?.currentOctave ?? 3) + 1) * 12;
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

            // Drawbar navigation and value control
            if (this.focusedDrawbar) {
                const drawbars = document.querySelectorAll('#drawbars .drawbar-slider');
                const currentIndex = parseInt(this.focusedDrawbar.dataset.index);
                // Left/Right arrow: move focus (wrap)
                if (e.code === 'ArrowLeft') {
                    e.preventDefault();
                    let prevIndex = (currentIndex - 1 + drawbars.length) % drawbars.length;
                    drawbars[prevIndex].focus();
                    this.focusedDrawbar = drawbars[prevIndex];
                    return;
                }
                if (e.code === 'ArrowRight') {
                    e.preventDefault();
                    let nextIndex = (currentIndex + 1) % drawbars.length;
                    drawbars[nextIndex].focus();
                    this.focusedDrawbar = drawbars[nextIndex];
                    return;
                }
                // ArrowUp/ArrowDown: increment/decrement logic
                if (e.code === 'ArrowUp') {
                    e.preventDefault();
                    let val;
                    if (e.shiftKey) {
                        val = 1;
                    } else {
                        let step = (e.metaKey || e.ctrlKey) ? 0.1 : 0.01;
                        val = Math.min(1, parseFloat(this.focusedDrawbar.value) + step);
                    }
                    this.focusedDrawbar.value = val.toFixed(2);
                    UIStateManager.setDrawbarGain(currentIndex, val);
                    this.focusedDrawbar.dispatchEvent(new Event('input', { bubbles: true }));
                    return;
                }
                if (e.code === 'ArrowDown') {
                    e.preventDefault();
                    let val;
                    if (e.shiftKey) {
                        val = 0;
                    } else {
                        let step = (e.metaKey || e.ctrlKey) ? 0.1 : 0.01;
                        val = Math.max(0, parseFloat(this.focusedDrawbar.value) - step);
                    }
                    this.focusedDrawbar.value = val.toFixed(2);
                    UIStateManager.setDrawbarGain(currentIndex, val);
                    this.focusedDrawbar.dispatchEvent(new Event('input', { bubbles: true }));
                    return;
                }
            }

            // Ctrl+ArrowUp/Down: Octave navigation (when not focused on drawbar)
            if (!this.focusedDrawbar) {
                if (e.code === 'ArrowUp' && (e.ctrlKey || e.metaKey)) {
                    e.preventDefault();
                    window.changeOctave?.(1);
                    return;
                }
                if (e.code === 'ArrowDown' && (e.ctrlKey || e.metaKey)) {
                    e.preventDefault();
                    window.changeOctave?.(-1);
                    return;
                }
            }
        });
    }
}
