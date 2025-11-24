
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
        this.component.onChange = (i, val) => {
            DrawbarsActions.setDrawbar(i, val);
        }

        this.setupEvents();
    }


    setupEvents() {

        // Whenever drawbar values change, update sliders
        // document.addEventListener("drawbar-change", () => {
        //     drawbars.update();
        // });

        document.addEventListener("drawbars-randomized", () => this.update());
        document.addEventListener("drawbars-reset", () => this.update());

        // Update labels when spectral system changes
        document.addEventListener("spectral-system-changed", () => {
            this.update();
        });
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
