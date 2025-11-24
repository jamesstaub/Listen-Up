
// controller/DrawbarController.js
import { Drawbars } from "./Drawbars.js";

import { AppState } from "../../config.js";
import { DrawbarsActions } from "./drawbarsActions.js";



export class DrawbarsController {
    constructor() {
        this.component = new Drawbars("drawbars");
    }

    init() {
        this.component.render();

        // connect component → actions
        this.component.onChange = (i, val) =>
            DrawbarsActions.setDrawbar(i, val);

        this.setupDrawbarEvents();
    }


    setupDrawbarEvents() {

        // Whenever a spectral system loads, rebuild the drawbars
        document.addEventListener("system-loaded", () => {
            drawbars.render();
        });

        // Whenever drawbar values change, update sliders
        document.addEventListener("drawbar-change", () => {
            drawbars.update();
        });

        document.addEventListener("drawbars-randomized", () => this.update());
        document.addEventListener("drawbars-reset", () => this.update());
    }

    randomize() {
        DrawbarsActions.randomize();
    }

    reset() {
        DrawbarsActions.reset();
    }

    update() {
        this.component.render();
    }

}
