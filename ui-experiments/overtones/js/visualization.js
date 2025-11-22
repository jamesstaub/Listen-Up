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

// ================================
// VISUALIZATION STATE
// ================================

let spreadFactor = 0.2;
let baseRadius;
let maxAmplitudeRadial;
const baseRadiusRatio = 0.25;

// ================================
// P5.JS SKETCH CONFIGURATION
// ================================

export function createVisualizationSketch() {
    return function(p) {
        // Store p5 instance reference
        AppState.p5Instance = p;

        // ================================
        // SETUP AND INITIALIZATION
        // ================================

        p.setup = function() {
            const container = document.getElementById('tonewheel-container');
            let w = container ? container.clientWidth - 40 : 800; // Account for padding
            let h = window.innerWidth < 640 ? 300 : 400; // Slightly smaller height
            
            // Fallback if container width is 0
            if (w === 0) {
                w = window.innerWidth < 640 ? 320 : 800;
                console.warn('Canvas container width was 0, using fallback width:', w);
            }
            
            p.createCanvas(w, h).parent(container ? 'tonewheel-container' : 'body');
            p.angleMode(p.RADIANS);
            
            updateDimensions();
            showStatus("Visualization initialized. Ready to play and export.", 'info');
        };

        // ================================
        // DIMENSION CALCULATIONS
        // ================================

        function updateDimensions() {
            const radialHeight = p.height * CANVAS_HEIGHT_RATIOS.RADIAL;
            maxAmplitudeRadial = p.min(p.width, radialHeight) * (1 - baseRadiusRatio) * 0.45;
            baseRadius = p.min(p.width, radialHeight) * baseRadiusRatio;
        }

        p.updateDimensions = updateDimensions;

        // ================================
        // WAVEFORM CALCULATION
        // ================================

        // Cache for custom waveform lookup tables to avoid recalculating Fourier series
        p.customWaveTables = {};
        
        p.getWaveValue = function(type, theta) {
            if (type.startsWith('custom')) {
                // For custom waveforms, use precomputed lookup table
                if (AppState.customWaveCoefficients && AppState.customWaveCoefficients[type]) {
                    // Check if we have a cached lookup table for this waveform
                    if (!p.customWaveTables[type]) {
                        // Precompute the waveform lookup table
                        p.customWaveTables[type] = p.precomputeCustomWaveTable(AppState.customWaveCoefficients[type]);
                    }
                    
                    // Use lookup table with linear interpolation
                    const table = p.customWaveTables[type];
                    const normalizedTheta = (theta % p.TWO_PI) / p.TWO_PI; // Normalize to 0-1
                    const index = normalizedTheta * (table.length - 1);
                    const lowIndex = Math.floor(index);
                    const highIndex = Math.ceil(index);
                    const fraction = index - lowIndex;
                    
                    if (lowIndex === highIndex) {
                        return table[lowIndex];
                    } else {
                        return table[lowIndex] * (1 - fraction) + table[highIndex] * fraction;
                    }
                } else {
                    // Fallback to sine if coefficients not found
                    return p.sin(theta);
                }
            }
            
            if (type === 'sine') {
                return p.sin(theta);
            }
            
            let sum = 0;
            let multiplier = 1;

            if (type === 'square') {
                for (let n = 1; n < VISUAL_HARMONIC_TERMS * 2; n += 2) {
                    sum += (1 / n) * p.sin(theta * n);
                    multiplier = 4 / p.PI;
                }
            } else if (type === 'sawtooth') {
                for (let n = 1; n <= VISUAL_HARMONIC_TERMS; n++) {
                    sum += (1 / n) * p.sin(theta * n);
                    multiplier = 2 / p.PI;
                }
            } else if (type === 'triangle') {
                for (let n = 1; n < VISUAL_HARMONIC_TERMS * 2; n += 2) {
                    const sign = ((n - 1) / 2) % 2 === 0 ? 1 : -1;
                    sum += (sign / (n * n)) * p.sin(theta * n);
                    multiplier = 8 / (p.PI * p.PI);
                }
            }

            return sum * multiplier * 0.7;
        };

        // Precompute custom waveform lookup table for performance
        p.precomputeCustomWaveTable = function(coeffs) {
            const tableSize = 512; // Good balance between memory and accuracy
            const table = new Float32Array(tableSize);
            
            for (let i = 0; i < tableSize; i++) {
                const theta = (i / tableSize) * p.TWO_PI;
                let sum = 0;
                
                // Reconstruct waveform from Fourier series: sum of real*cos + imag*sin
                for (let k = 1; k < coeffs.real.length && k < coeffs.imag.length; k++) {
                    sum += coeffs.real[k] * p.cos(k * theta) + coeffs.imag[k] * p.sin(k * theta);
                }
                table[i] = sum;
            }
            
            return table;
        };
        
        // Clear cache when new waveforms are added
        p.clearCustomWaveCache = function() {
            p.customWaveTables = {};
        };

        // ================================
        // RADIAL DISPLAY (TONEWHEEL)
        // ================================

        function drawRadialDisplay() {
            const radialHeight = p.height * CANVAS_HEIGHT_RATIOS.RADIAL;
            
            p.push();
            p.translate(p.width / 2, radialHeight / 2);

            // Draw base circle
            p.noFill();
            p.stroke('#374151');
            p.ellipse(0, 0, baseRadius * 2, baseRadius * 2);

            const points = 360;
            // Convert visualization frequency (Hz) to rotation speed (radians per frame)
            // At 60 FPS, 1 Hz = 2π/60 radians per frame
            let rotationSpeed = (AppState.visualizationFrequency * p.TWO_PI) / 60;
            let currentAngle = p.frameCount * rotationSpeed;

            // 1. Draw Individual Partials
            drawIndividualPartials(points, currentAngle);

            // 2. Draw the Final Summed Waveform
            drawSummedWaveform(points, currentAngle);

            p.pop();
        }

        function drawIndividualPartials(points, currentAngle) {
            for (let h = 0; h < AppState.harmonicAmplitudes.length; h++) {
                const ratio = AppState.currentSystem.ratios[h];
                const amp = AppState.harmonicAmplitudes[h] * maxAmplitudeRadial * (1 / 12);
                
                // Calculate radial offset with proper spacing to prevent overlap at max spread
                let radialOffset = 0;
                if (spreadFactor > 0) {
                    const maxWaveAmplitude = maxAmplitudeRadial * (1 / 12);
                    const spacingBuffer = maxWaveAmplitude * 2.5;
                    const totalAvailableSpace = maxAmplitudeRadial * 0.8;
                    const activeHarmonics = AppState.harmonicAmplitudes.filter(a => a > 0.005).length;
                    
                    if (activeHarmonics > 1) {
                        const maxSpacing = totalAvailableSpace / (activeHarmonics - 1);
                        const actualSpacing = Math.min(spacingBuffer, maxSpacing);
                        
                        // Count active harmonics before this one
                        let activeIndex = 0;
                        for (let i = 0; i < h; i++) {
                            if (AppState.harmonicAmplitudes[i] > 0.005) activeIndex++;
                        }
                        
                        // Only apply offset if this harmonic is active
                        if (AppState.harmonicAmplitudes[h] > 0.005) {
                            radialOffset = actualSpacing * activeIndex * spreadFactor;
                        }
                    }
                }

                if (amp > 0.005) {
                    p.stroke(p.color(HARMONIC_COLORS[h] + '99'));
                    p.strokeWeight(1.5);
                    p.noFill();
                    p.beginShape();
                    
                    let totalRadialBase = baseRadius + radialOffset;
                    let visualizationRatio = ratio;
                    let visualAmpScale = AppState.isSubharmonic ? (1 / ratio) : ratio;

                    for (let i = 0; i < points; i++) {
                        let theta = p.map(i, 0, points, 0, p.TWO_PI);
                        
                        // In subharmonic mode, multiply the visualization ratio to show more detail
                        let adjustedRatio = AppState.isSubharmonic ? visualizationRatio * 3 : visualizationRatio;
                        let waveValue = p.getWaveValue(AppState.currentWaveform, adjustedRatio * theta + currentAngle);
                        
                        let r = totalRadialBase + waveValue * amp * visualAmpScale * 0.5;
                        
                        let x = r * p.cos(theta);
                        let y = r * p.sin(theta);
                        p.vertex(x, y);
                    }
                    p.endShape(p.CLOSE);
                }
            }
        }

        function drawSummedWaveform(points, currentAngle) {
            p.strokeWeight(0);
            p.fill(16, 185, 129, 37);
            
            p.beginShape();
            for (let i = 0; i < points; i++) {
                let theta = p.map(i, 0, points, 0, p.TWO_PI);
                
                let r = baseRadius;
                for (let h = 0; h < AppState.harmonicAmplitudes.length; h++) {
                    const ratio = AppState.currentSystem.ratios[h];
                    const amp = AppState.harmonicAmplitudes[h] * maxAmplitudeRadial;
                    
                    r += p.getWaveValue(AppState.currentWaveform, ratio * theta + currentAngle) * amp / (ratio * 2);
                }

                let x = r * p.cos(theta);
                let y = r * p.sin(theta);
                p.vertex(x, y);
            }
            p.endShape(p.CLOSE);
        }

        // ================================
        // OSCILLOSCOPE DISPLAY
        // ================================

        function drawOscilloscope() {
            const oscHeight = p.height * CANVAS_HEIGHT_RATIOS.OSCILLOSCOPE;
            const oscY = p.height * CANVAS_HEIGHT_RATIOS.RADIAL; // Start right after the radial display
            const ampScale = oscHeight * 0.4;
            const points = p.width;

            p.push();
            p.translate(0, oscY);

            // Background
            p.fill('#1f2937');
            p.noStroke();
            p.rect(0, 0, p.width, oscHeight, 0.5 * 10, 0.5 * 10, 0, 0);

            // Center line
            p.stroke('#374151');
            p.strokeWeight(1);
            p.line(0, oscHeight / 2, p.width, oscHeight / 2);

            // Label
            p.textAlign(p.LEFT, p.TOP);
            p.textSize(10);
            

            // Waveform
            p.stroke('#10b981');
            p.strokeWeight(2.5);
            p.noFill();
            p.beginShape();

            for (let x = 0; x < points; x++) {
                let theta = p.map(x, 0, points, 0, p.TWO_PI);
                
                let summedWave = 0;
                let maxPossibleAmp = 0;

                for (let h = 0; h < AppState.harmonicAmplitudes.length; h++) {
                    const ratio = AppState.currentSystem.ratios[h];
                    const amp = AppState.harmonicAmplitudes[h];
                    
                    summedWave += p.getWaveValue(AppState.currentWaveform, ratio * theta) * amp;
                    maxPossibleAmp += amp;
                }
                
                const normalizedWave = summedWave / (maxPossibleAmp || 1);
                let y = oscHeight / 2 - normalizedWave * ampScale;
                p.vertex(x, y);
            }
            p.endShape();
            p.pop();
        }

        // ================================
        // MAIN DRAW LOOP
        // ================================

        p.draw = function() {
            p.background('#0d131f');
            updateDimensions();
            
            drawRadialDisplay();
            // Temporarily disable oscilloscope to focus on tonewheel
            // drawOscilloscope(); 
        };

        // ================================
        // VISUALIZATION CONTROL FUNCTIONS
        // ================================

        p.setSpreadFactor = function(value) {
            spreadFactor = value;
        };

        p.getSpreadFactor = function() {
            return spreadFactor;
        };

        // ================================
        // RESPONSIVENESS
        // ================================

        p.windowResized = function() {
            const container = document.getElementById('tonewheel-container');
            let w = container ? container.clientWidth - 40 : 800;
            let h = window.innerWidth < 640 ? 500 : 600;
            
            // Fallback if container width is 0
            if (w === 0) {
                w = window.innerWidth < 640 ? 320 : 800;
            }
            
            p.resizeCanvas(w, h);
            updateDimensions();
        };
    };
}

// ================================
// VISUALIZATION CONTROL INTERFACE
// ================================

/**
 * Updates the spread factor for the visualization
 * @param {number} value - Spread factor value (0-1)
 */
export function setSpreadFactor(value) {
    if (AppState.p5Instance && AppState.p5Instance.setSpreadFactor) {
        AppState.p5Instance.setSpreadFactor(value);
    }
}

/**
 * Gets the current spread factor
 * @returns {number} Current spread factor
 */
export function getSpreadFactor() {
    if (AppState.p5Instance && AppState.p5Instance.getSpreadFactor) {
        return AppState.p5Instance.getSpreadFactor();
    }
    return 0.2;
}

/**
 * Clears custom waveform cache to free memory and ensure fresh calculations
 */
export function clearCustomWaveCache() {
    if (AppState.p5Instance && AppState.p5Instance.clearCustomWaveCache) {
        AppState.p5Instance.clearCustomWaveCache();
    }
}

// Create a separate p5 sketch for the linear waveform (oscilloscope)
function createWaveformSketch() {
    return function(p) {
        p.setup = function() {
            const container = document.getElementById('waveform-canvas-area');
            const w = container ? Math.max(300, container.clientWidth - 40) : 400;
            const h = 150;
            p.createCanvas(w, h).parent(container ? 'waveform-canvas-area' : document.body);
        };

        p.windowResized = function() {
            const container = document.getElementById('waveform-canvas-area');
            const w = container ? Math.max(300, container.clientWidth - 40) : 400;
            const h = 150;
            p.resizeCanvas(w, h);
        };

        p.draw = function() {
            p.background('#0d131f');

            // Draw oscilloscope using main p5 instance's waveform functions
            const mainP5 = AppState.p5Instance;
            const oscHeight = p.height;
            const ampScale = oscHeight * 0.4;

            // Background box
            p.noStroke();
            p.fill('#0d131f');
            p.rect(0, 0, p.width, p.height);

            // Center line
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

/**
 * Initializes the visualization system
 */
export function initVisualization() {
    // Create the tonewheel sketch and attach to its container
    const tonewheelSketch = createVisualizationSketch();
    new p5(tonewheelSketch, 'tonewheel-container');

    // Defer creation of the waveform sketch until the main p5 instance is available
    const tryCreateWaveform = () => {
        if (AppState.p5Instance && AppState.p5Instance.getWaveValue) {
            const waveformSketch = createWaveformSketch();
            new p5(waveformSketch, 'waveform-canvas-area');
        } else {
            // Retry shortly; ensures main p5 has set AppState.p5Instance
            setTimeout(tryCreateWaveform, 100);
        }
    };
    tryCreateWaveform();
}