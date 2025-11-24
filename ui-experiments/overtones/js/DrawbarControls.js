/**
 * Drawbar UI Module
 * Handles creation, updating, resetting, and randomizing drawbars
 */

import { AppState, DRAWBAR_STYLES } from './config.js';
import { smoothUpdateHarmonicAmplitude } from './utils.js';
import { UIStateManager } from './UIStateManager.js';




export function createDrawbar(index) {
    const styleClass = DRAWBAR_STYLES[index] || 'white';
    const initialValue = AppState.harmonicAmplitudes[index];

    const drawbarDiv = document.createElement('div');
    drawbarDiv.className = `drawbar ${styleClass}`;

    const labelSpan = document.createElement('span');
    labelSpan.className = 'drawbar-label';
    labelSpan.id = `drawbar-label-${index}`;
    // Use system label for this partial
    labelSpan.textContent = AppState.currentSystem.labels[index] || '';

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



export class DrawbarControls {
    constructor(containerId = 'drawbars') {
        this.container = document.getElementById(containerId);
        if (!this.container) throw new Error('Drawbar container not found');
        this.sliders = [];
        this.init();
    }

    // ================================
    // Instance Methods
    // ================================
    init() {

        this.setupResetButton();
        this.setupRandomizeButton();
        updateDrawbarLabels();
    }

    setupResetButton() {
        document.getElementById('reset-drawbars-button')?.addEventListener('click', () => {
            this.sliders.forEach((slider, idx) => {
                slider.value = idx === 0 ? slider.max : 0;
                UIStateManager.setDrawbarGain(idx, parseFloat(slider.value));
                slider.dispatchEvent(new Event('input', { bubbles: true }));
            });
        });
    }

    setupRandomizeButton() {
        document.getElementById('randomize-drawbars-button')?.addEventListener('click', () => {
            this.sliders.forEach((slider, idx) => {
                slider.value = idx === 0 ? (0.5 + Math.random() * 0.5).toFixed(2) : Math.random().toFixed(2);
                UIStateManager.setDrawbarGain(idx, parseFloat(slider.value));
                slider.dispatchEvent(new Event('input', { bubbles: true }));
            });
        });
    }

    // ================================
    // Static Convenience Methods
    // ================================
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
