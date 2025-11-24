import { AppState } from "../../config.js";

/**
 * ACTIONS MODULE
 * --------------
 * Central hub for mutating application state and broadcasting changes.
 *
 * This module defines the authoritative "write operations" for the app.
 * If something changes AppState, it happens here — nowhere else.
 *
 * RULES OF ACTIONS.JS
 * --------------------
 * 1. **State Changes Only**
 *    Every function here performs a state mutation:
 *      - updating drawbar values
 *      - randomizing amplitudes
 *      - resetting parameters
 *      - loading spectral systems
 *    No DOM manipulation, no rendering, no UI logic.
 *
 * 2. **Fire Semantic Global Events**
 *    After changing state, actions emit CustomEvents on `document`:
 *      document.dispatchEvent(new CustomEvent("whatever-changed", {...}))
 *
 *    These events signal that "the data changed," not "the UI needs to do X."
 *    Controllers and components can subscribe and react however they want.
 *    This keeps the app scalable and decoupled.
 *
 * 3. **No Direct DOM Access**
 *    Buttons, sliders, keyboard shortcuts, MIDI controllers — none of that
 *    should appear in this file. They call actions; actions never call them.
 *
 * 4. **UI Responds to Actions, Not Vice Versa**
 *    UI elements *listen* for the events fired here.
 *    This prevents circular logic and keeps business logic clean.
 *
 * 5. **Events Must Be High-Level and Meaningful**
 *    Good:
 *      "drawbar-change"
 *      "drawbars-randomized"
 *      "system-loaded"
 *
 *    Bad:
 *      "slider-input"
 *      "knob-clicked"
 *      "user-did-something"
 *
 *    Events describe *state transitions*, not *UI activities*.
 *
 * 6. **Pure Functions + Transparent Side Effects**
 *    Inside actions:
 *      - compute the new state
 *      - update AppState
 *      - fire the event
 *    No hidden magic.
 *
 * WHY THIS EXISTS
 * ---------------
 * It creates a clean separation between:
 *    - Components (visual DOM pieces)
 *    - Controllers (event wiring: UI → actions)
 *    - Actions (state updates + global signals)
 *
 * With MIDI, keyboard shortcuts, UI widgets, and future modules all funneling
 * into the same action layer, the app stays predictable and maintainable.
 */

export const DrawbarsActions = {
    setDrawbar(index, value) {
        AppState.harmonicAmplitudes[index] = value;

        // used to be UIStateManager.setDrawbarGain()
        AppState.drawbarGains[index] = value;

        // Fire update event (replaces dispatchEvent in old DrawbarControls)
        document.dispatchEvent(
            new CustomEvent("drawbar-change", {
                detail: { index, value }
            })
        );
    },

    randomize() {
        AppState.harmonicAmplitudes = AppState.harmonicAmplitudes.map(
            (_, i) => (i === 0 ? 0.5 + Math.random() * 0.5 : Math.random())
        );

        document.dispatchEvent(new Event("drawbars-randomized"));
    },

    reset() {
        AppState.harmonicAmplitudes = AppState.harmonicAmplitudes.map(
            (_, i) => (i === 0 ? 1 : 0)
        );

        document.dispatchEvent(new Event("drawbars-reset"));
    }
};
