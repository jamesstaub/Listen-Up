/**
 * VISUALIZATION MODULE
 * Contains P5.js sketch and visualization logic for the spectral synthesizer
 */

import {
    AppState,
    updateAppState,
    VISUAL_HARMONIC_TERMS,
    CANVAS_HEIGHT_RATIOS,
    HARMONIC_COLORS
} from './config.js';
import { showStatus } from './utils.js';

let spreadFactor = 1;
let baseRadius;
let maxAmplitudeRadial;
const baseRadiusRatio = 0.08; // Smaller fundamental, more spread
const VISUALIZER_AMPLITUDE_SCALE = 16;

// ================================
// P5.JS SKETCH CONFIGURATION
// ================================

export function createVisualizationSketch() {
    return function(p) {
        AppState.p5Instance = p;

        // ================================
        // SETUP
        // ================================

        p.setup = function() {
            const container = document.getElementById('tonewheel-container');
            let w = container ? container.clientWidth : 800;
            let h = w;
            if (w === 0) {
                w = window.innerWidth < 640 ? 320 : 800;
                h = w;
                console.warn('Canvas container width was 0, using fallback width:', w);
            }
            p.createCanvas(w, h).parent(container ? 'tonewheel-container' : 'body');
            p.angleMode(p.RADIANS);
            updateDimensions();
        };

        function updateDimensions() {
            const radialHeight = p.height * CANVAS_HEIGHT_RATIOS.RADIAL;
            maxAmplitudeRadial = p.min(p.width, radialHeight) * (1 - baseRadiusRatio) * 0.45;
            baseRadius = p.min(p.width, radialHeight) * baseRadiusRatio;
        }

        p.updateDimensions = updateDimensions;

        // ================================
        // WAVEFORM CALCULATION
        // ================================

        p.customWaveTables = {};

        p.getWaveValue = function(type, theta) {
            if (type.startsWith('custom')) {
                if (AppState.customWaveCoefficients && AppState.customWaveCoefficients[type]) {
                    if (!p.customWaveTables[type]) {
                        p.customWaveTables[type] = p.precomputeCustomWaveTable(AppState.customWaveCoefficients[type]);
                    }
                    const table = p.customWaveTables[type];
                    const normalizedTheta = (theta % p.TWO_PI) / p.TWO_PI;
                    const index = normalizedTheta * (table.length - 1);
                    const lowIndex = Math.floor(index);
                    const highIndex = Math.ceil(index);
                    const fraction = index - lowIndex;
                    return lowIndex === highIndex ? table[lowIndex] : table[lowIndex] * (1 - fraction) + table[highIndex] * fraction;
                } else {
                    return p.sin(theta);
                }
            }

            if (type === 'sine') return p.sin(theta);

            let sum = 0, multiplier = 1;
            if (type === 'square') {
                for (let n = 1; n < VISUAL_HARMONIC_TERMS * 2; n += 2) sum += (1 / n) * p.sin(theta * n), multiplier = 4 / p.PI;
            } else if (type === 'sawtooth') {
                for (let n = 1; n <= VISUAL_HARMONIC_TERMS; n++) sum += (1 / n) * p.sin(theta * n), multiplier = 2 / p.PI;
            } else if (type === 'triangle') {
                for (let n = 1; n < VISUAL_HARMONIC_TERMS * 2; n += 2) {
                    const sign = ((n - 1) / 2) % 2 === 0 ? 1 : -1;
                    sum += (sign / (n * n)) * p.sin(theta * n);
                    multiplier = 8 / (p.PI * p.PI);
                }
            }
            return sum * multiplier * 0.7;
        };

        p.precomputeCustomWaveTable = function(coeffs) {
            const tableSize = 512;
            const table = new Float32Array(tableSize);
            for (let i = 0; i < tableSize; i++) {
                const theta = (i / tableSize) * p.TWO_PI;
                let sum = 0;
                for (let k = 1; k < coeffs.real.length && k < coeffs.imag.length; k++) {
                    sum += coeffs.real[k] * p.cos(k * theta) + coeffs.imag[k] * p.sin(k * theta);
                }
                table[i] = sum;
            }
            return table;
        };

        p.clearCustomWaveCache = function() {
            p.customWaveTables = {};
        };

        // ================================
        // RADIAL DISPLAY (TONEWHEEL)
        // ================================

        function computeHarmonicLaneRadii({ harmonicAmplitudes, inner = 0.1, outer = 0.95 }) {
            // only include active harmonics
            const activeAmps = harmonicAmplitudes.map((amp, idx) => ({amp, idx})).filter(x => x.amp > 0);
            const lanes = activeAmps.length;
            const radiiNorm = new Array(lanes);
            for (let i = 0; i < lanes; i++) {
                radiiNorm[i] = inner + (outer - inner) * (i / (lanes - 1 || 1)); // normalize 0–1
            }
            // map back to original indices
            const fullRadii = new Array(harmonicAmplitudes.length).fill(null);
            activeAmps.forEach((x, i) => fullRadii[x.idx] = radiiNorm[i]);
            return fullRadii;
        }

        function drawRadialDisplay() {
            p.push();
            p.translate(p.width / 2, p.height / 2);

            p.noFill();
            p.stroke('#374151');
            p.ellipse(0, 0, baseRadius * 2, baseRadius * 2);

            const points = 360;
            const rotationSpeed = (AppState.visualizationFrequency * p.TWO_PI) / 60;
            const currentAngle = p.frameCount * rotationSpeed;

            drawIndividualPartials(points, currentAngle);
            drawSummedWaveform(points, currentAngle);
            p.pop();
        }

        function drawIndividualPartials(points, currentAngle) {
            const numHarmonics = AppState.harmonicAmplitudes.length;
            const radiiNorm = computeHarmonicLaneRadii({ harmonicAmplitudes: AppState.harmonicAmplitudes });
            const maxCanvasRadius = Math.min(p.width, p.height) * 0.5;
            const radii = radiiNorm.map(r => r === null ? 0 : r * maxCanvasRadius);

            for (let h = 0; h < numHarmonics; h++) {
                const amp = AppState.harmonicAmplitudes[h];
                if (amp <= 0) continue;

                const ratio = AppState.currentSystem.ratios[h];
                const ringRadius = radii[h];
                const visualAmp = amp * 0.45 * VISUALIZER_AMPLITUDE_SCALE; // only affects displacement

                p.stroke(p.color(HARMONIC_COLORS[h] + '99'));
                p.strokeWeight(1.5);
                p.noFill();
                p.beginShape();
                for (let i = 0; i < points; i++) {
                    const theta = p.map(i, 0, points, 0, p.TWO_PI);
                    const waveValue = p.getWaveValue(AppState.currentWaveform, ratio * theta);
                    const r = ringRadius + waveValue * visualAmp;
                    const x = r * Math.cos(theta + currentAngle);
                    const y = r * Math.sin(theta + currentAngle);
                    p.vertex(x, y);
                }
                p.endShape(p.CLOSE);
            }
        }

        function drawSummedWaveform(points, currentAngle) {
            p.strokeWeight(0);
            p.fill(16, 185, 129, 15);

            p.beginShape();
            for (let i = 0; i < points; i++) {
                const theta = p.map(i, 0, points, 0, p.TWO_PI);
                let r = baseRadius;
                for (let h = 0; h < AppState.harmonicAmplitudes.length; h++) {
                    const amp = AppState.harmonicAmplitudes[h] * maxAmplitudeRadial;
                    const ratio = AppState.currentSystem.ratios[h];
                    r += p.getWaveValue(AppState.currentWaveform, ratio * theta + currentAngle) * amp / (ratio * 2);
                }
                const x = r * Math.cos(theta);
                const y = r * Math.sin(theta);
                p.vertex(x, y);
            }
            p.endShape(p.CLOSE);
        }

        // ================================
        // MAIN DRAW LOOP
        // ================================

        p.draw = function() {
            p.background('#0d131f');
            updateDimensions();
            drawRadialDisplay();
            // drawOscilloscope();
        };

        // ================================
        // RESPONSIVENESS
        // ================================

        p.windowResized = function() {
            const container = document.getElementById('tonewheel-container');
            let w = container ? container.clientWidth : 800;
            let h = w;
            if (w === 0) {
                w = window.innerWidth < 640 ? 320 : 800;
                h = w;
            }
            p.resizeCanvas(w, h);
            updateDimensions();
        };
    };
}

// ================================
// INTERFACE FUNCTIONS
// ================================

export function setSpreadFactor(value) {
    if (AppState.p5Instance && AppState.p5Instance.setSpreadFactor) {
        AppState.p5Instance.setSpreadFactor(value);
    }
}

export function getSpreadFactor() {
    if (AppState.p5Instance && AppState.p5Instance.getSpreadFactor) {
        return AppState.p5Instance.getSpreadFactor();
    }
    return 0.2;
}

export function clearCustomWaveCache() {
    if (AppState.p5Instance && AppState.p5Instance.clearCustomWaveCache) {
        AppState.p5Instance.clearCustomWaveCache();
    }
}

// ================================
// WAVEFORM SKETCH
// ================================

function createWaveformSketch() {
    return function(p) {
        p.setup = function() {
            const container = document.getElementById('waveform-canvas-area');
            const w = container ? container.clientWidth : 400;
            const h = 150;
            p.createCanvas(w, h).parent(container ? 'waveform-canvas-area' : document.body);
        };

        p.windowResized = function() {
            const container = document.getElementById('waveform-canvas-area');
            const w = container ? container.clientWidth : 400;
            const h = 150;
            p.resizeCanvas(w, h);
        };

        p.draw = function() {
            p.background('#0d131f');
            const mainP5 = AppState.p5Instance;
            const oscHeight = p.height;
            const ampScale = oscHeight * 0.4;
            p.noStroke();
            p.fill('#0d131f');
            p.rect(0, 0, p.width, p.height);
            p.stroke('#374151');
            p.strokeWeight(1);
            p.line(0, oscHeight / 2, p.width, oscHeight / 2);

            if (!mainP5 || !mainP5.getWaveValue) return;

            p.stroke('#10b981');
            p.strokeWeight(2);
            p.noFill();
            p.beginShape();
            const points = p.width;
            for (let x = 0; x < points; x++) {
                const theta = p.map(x, 0, points, 0, p.TWO_PI * 2);
                let summedWave = 0;
                let maxPossibleAmp = 0;
                for (let hIdx = 0; hIdx < AppState.harmonicAmplitudes.length; hIdx++) {
                    const ratio = AppState.currentSystem.ratios[hIdx];
                    const amp = AppState.harmonicAmplitudes[hIdx] || 0;
                    summedWave += mainP5.getWaveValue(AppState.currentWaveform, ratio * theta) * amp;
                    maxPossibleAmp += amp;
                }
                const normalizedWave = summedWave / (maxPossibleAmp || 1);
                const y = oscHeight / 2 - normalizedWave * ampScale;
                p.vertex(x, y);
            }
            p.endShape();
        };
    };
}

// ================================
// INITIALIZATION
// ================================

export function initVisualization() {
    const tonewheelSketch = createVisualizationSketch();
    new p5(tonewheelSketch, 'tonewheel-container');

    const tryCreateWaveform = () => {
        if (AppState.p5Instance && AppState.p5Instance.getWaveValue) {
            const waveformSketch = createWaveformSketch();
            new p5(waveformSketch, 'waveform-canvas-area');
        } else {
            setTimeout(tryCreateWaveform, 100);
        }
    };
    tryCreateWaveform();
}
