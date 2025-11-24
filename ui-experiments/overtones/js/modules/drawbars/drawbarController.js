
// controller/DrawbarController.js
import { Drawbars } from "../components/Drawbars.js";
import { DrawbarActions } from "../actions/drawbarActions.js";
import { AppState } from "../../config.js";


export class DrawbarController {
    constructor() {
        this.component = new Drawbars(
            document.getElementById("drawbars")
        );
    }

    init() {
        this.component.render(
            AppState.currentSystem,
            AppState.harmonicAmplitudes
        );

        // connect component → actions
        this.component.onChange = (i, val) =>
            DrawbarActions.setDrawbar(i, val);

        // react to randomize/reset from actions
        document.addEventListener("drawbars-randomized", () =>
            this.updateUI()
        );

        document.addEventListener("drawbars-reset", () =>
            this.updateUI()
        );
    }

    updateUI() {
        this.component.render(
            AppState.currentSystem,
            AppState.harmonicAmplitudes
        );
    }
}
