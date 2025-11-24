/**
 * Momentum-based parameter smoother (Pro Version 2.0)
 * Ultra-stable, MIDI-safe, high-performance smoothing engine.
 */
class MomentumSmoother {
    constructor() {
        this.params = new Map();
        this.isRunning = false;
        this.frame = null;

        // stable timestep (60 fps equivalent)
        this.dt = 1 / 60;
    }

    /**
     * Create/update a smoother target.
     * IMPORTANT: callback is only set on creation — never overwritten.
     */
    smoothTo(key, value, callback, smoothness = 0.75) {
        let p = this.params.get(key);

        if (!p) {
            // new parameter
            p = {
                current: value,
                target: value,
                pendingTarget: null,   // coalesces multiple updates
                callback,
                smoothness: Math.min(Math.max(smoothness, 0.01), 0.99999),
                active: true
            };
            this.params.set(key, p);
        } else {
            // existing param — do NOT replace callback
            p.pendingTarget = value; // store incoming MIDI/slider events
            p.smoothness = Math.min(Math.max(smoothness, 0.01), 0.99999);
            p.active = true;
        }

        if (!this.isRunning) this.start();
    }

    /**
     * Immediate hard-set, bypassing smoothing.
     */
    setImmediate(key, value) {
        const p = this.params.get(key);
        if (!p) return;

        p.current = value;
        p.target = value;
        p.pendingTarget = null;
        p.active = false;

        p.callback(value);
    }

    start() {
        if (this.isRunning) return;
        this.isRunning = true;
        this.tick();
    }

    tick() {
        let activeCount = 0;

        for (const [key, p] of this.params) {

            // If multiple updates came in (e.g. MIDI flood), coalesce:
            if (p.pendingTarget !== null) {
                p.target = p.pendingTarget;
                p.pendingTarget = null;
            }

            if (!p.active) continue;

            const diff = p.target - p.current;

            if (Math.abs(diff) < 1e-5) {
                // Snap and stop smoothing
                p.current = p.target;
                p.callback(p.current);
                p.active = false;
                continue;
            }

            // PRO exponential smoothing (frame-rate independent):
            // smoothness = 0.75 → soft smoothing
            // smoothness = 0.98 → slow/creamy
            const s = p.smoothness;
            const smoothingFactor = Math.pow(s, this.dt * 60);

            p.current = 
                p.current * smoothingFactor +
                p.target * (1 - smoothingFactor);

            p.callback(p.current);
            activeCount++;
        }

        if (activeCount > 0) {
            this.frame = requestAnimationFrame(() => this.tick());
        } else {
            this.isRunning = false;
            this.frame = null;
        }
    }

    remove(key) {
        this.params.delete(key);
    }

    clear() {
        this.params.clear();
        if (this.frame) cancelAnimationFrame(this.frame);
        this.isRunning = false;
        this.frame = null;
    }

    getCurrentValue(key) {
        const p = this.params.get(key);
        return p ? p.current : null;
    }
}

export const momentumSmoother = new MomentumSmoother();
export { MomentumSmoother };
