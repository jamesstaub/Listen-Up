
// controller/DrawbarController.js
import { DrawbarsComponent } from "./DrawbarsComponent.js";
import { DrawbarsActions } from "./drawbarsActions.js";

export class DrawbarsController {
    constructor() {
        this.component = new DrawbarsComponent("drawbars");
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
        // document.addEventListener("system-loaded", () => {
        //     drawbars.render();
        // });

        // Whenever drawbar values change, update sliders
        // TODO: do we need this?
        // document.addEventListener("drawbar-change", () => {
        //     drawbars.update();
        // });

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
