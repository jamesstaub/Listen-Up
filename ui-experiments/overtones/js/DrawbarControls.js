// DrawbarControls.js
// Manages drawbar UI, randomize/reset, focus, and gain changes
import { UIStateManager } from './UIStateManager.js';

export class DrawbarControls {
    static randomizeDrawbars() {
        const drawbars = document.querySelectorAll('#drawbars .drawbar-slider');
        drawbars.forEach((slider, idx) => {
            slider.value = idx === 0 ? (0.5 + Math.random() * 0.5).toFixed(2) : Math.random().toFixed(2);
            UIStateManager.setDrawbarGain(idx, parseFloat(slider.value));
            slider.dispatchEvent(new Event('input', { bubbles: true }));
        });
    }
    static resetDrawbars() {
        const drawbars = document.querySelectorAll('#drawbars .drawbar-slider');
        drawbars.forEach((slider, idx) => {
            slider.value = idx === 0 ? slider.max : 0;
            UIStateManager.setDrawbarGain(idx, parseFloat(slider.value));
            slider.dispatchEvent(new Event('input', { bubbles: true }));
        });
    }
}
