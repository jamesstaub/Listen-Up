import { AppState, DRAWBAR_STYLES } from "../../config.js";


// components/Drawbars.js
export class DrawbarsComponent {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.sliders = [];
    }

    render() {
        this.sliders = [];
        this.setupDrawbars();
        this.updateDrawbarLabels();
    }

    setupDrawbars() {
        this.container.innerHTML = '';
        const numPartials = AppState.currentSystem.ratios.length;

        // Ensure AppState.harmonicAmplitudes is the correct length
        if (!Array.isArray(AppState.harmonicAmplitudes) || AppState.harmonicAmplitudes.length !== numPartials) {
            AppState.harmonicAmplitudes = Array(numPartials).fill(0);
            AppState.harmonicAmplitudes[0] = 1.0;
        }

        for (let i = 0; i < numPartials; i++) {
            const drawbarDiv = this.createDrawbar(i, AppState.harmonicAmplitudes[i]);
            this.container.appendChild(drawbarDiv);
        }
    }

    updateDrawbarLabels() {
        AppState.currentSystem.labels.forEach((label, index) => {
            const labelElement = document.getElementById(`drawbar-label-${index}`);
            if (labelElement) {
                labelElement.textContent = label;
            }
        });
    }



    createDrawbar(index, value) {
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
        input.value = value;

        input.addEventListener('input', this.handleDrawbarChange.bind(this));

        inputWrapper.appendChild(trackDiv);
        inputWrapper.appendChild(input);
        drawbarDiv.appendChild(labelSpan);
        drawbarDiv.appendChild(inputWrapper);

        return drawbarDiv;
    }

    handleDrawbarChange(e) {
    const index = parseInt(e.target.dataset.index);
    const value = parseFloat(e.target.value);

    // Notify the controller/app via callback
    this.onChange?.(index, value);

    // Optionally update ARIA attribute
    e.target.setAttribute('aria-valuenow', value);
    }

    setValue(index, value) {
        this.sliders[index].value = value;
    }
}
