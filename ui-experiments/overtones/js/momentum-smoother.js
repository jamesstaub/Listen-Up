/**
 * MOMENTUM SMOOTHER MODULE
 * Continuous parameter smoothing without debouncing delays
 */

/**
 * Momentum-based parameter smoother for immediate responsive control
 * without audible artifacts
 */
class MomentumSmoother {
    constructor() {
        this.smoothers = new Map();
        this.isRunning = false;
        this.animationFrame = null;
    }

    /**
     * Creates or updates a parameter smoother
     * @param {string} key - Unique parameter key
     * @param {number} targetValue - Target value to smooth towards
     * @param {Function} updateCallback - Function to call with smoothed value
     * @param {number} smoothness - Smoothness factor (0.1 = fast, 0.9 = slow)
     */
    smoothTo(key, targetValue, updateCallback, smoothness = 0.85) {
        if (!this.smoothers.has(key)) {
            this.smoothers.set(key, {
                current: targetValue,
                target: targetValue,
                callback: updateCallback,
                smoothness: smoothness,
                lastUpdate: performance.now()
            });
        } else {
            const smoother = this.smoothers.get(key);
            smoother.target = targetValue;
            smoother.callback = updateCallback;
            smoother.smoothness = smoothness;
        }

        this.startSmoothing();
    }

    /**
     * Starts the smoothing animation loop
     */
    startSmoothing() {
        if (this.isRunning) return;
        
        this.isRunning = true;
        this.tick();
    }

    /**
     * Main smoothing loop
     */
    tick() {
        const now = performance.now();
        let hasActiveSmoothing = false;

        for (const [key, smoother] of this.smoothers) {
            const deltaTime = (now - smoother.lastUpdate) / 16.67; // Normalize to 60fps
            const diff = smoother.target - smoother.current;
            
            // Check if we need to continue smoothing
            if (Math.abs(diff) > 0.0001) {
                // Apply exponential smoothing with time compensation
                const smoothingFactor = Math.pow(smoother.smoothness, deltaTime);
                smoother.current = smoother.current * smoothingFactor + smoother.target * (1 - smoothingFactor);
                
                // Call the update callback
                smoother.callback(smoother.current);
                hasActiveSmoothing = true;
            } else {
                // Snap to target when very close
                if (smoother.current !== smoother.target) {
                    smoother.current = smoother.target;
                    smoother.callback(smoother.current);
                }
            }
            
            smoother.lastUpdate = now;
        }

        if (hasActiveSmoothing) {
            this.animationFrame = requestAnimationFrame(() => this.tick());
        } else {
            this.isRunning = false;
            this.animationFrame = null;
        }
    }

    /**
     * Immediately sets a parameter value without smoothing
     * @param {string} key - Parameter key
     * @param {number} value - Value to set
     */
    setImmediate(key, value) {
        if (this.smoothers.has(key)) {
            const smoother = this.smoothers.get(key);
            smoother.current = value;
            smoother.target = value;
            smoother.callback(value);
        }
    }

    /**
     * Removes a parameter from smoothing
     * @param {string} key - Parameter key to remove
     */
    remove(key) {
        this.smoothers.delete(key);
    }

    /**
     * Clears all smoothers
     */
    clear() {
        this.smoothers.clear();
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
        }
        this.isRunning = false;
    }

    /**
     * Gets the current value of a parameter
     * @param {string} key - Parameter key
     * @returns {number|null} Current value or null if not found
     */
    getCurrentValue(key) {
        const smoother = this.smoothers.get(key);
        return smoother ? smoother.current : null;
    }
}

// Create and export a global instance
export const momentumSmoother = new MomentumSmoother();

// Also export the class for potential future use
export { MomentumSmoother };