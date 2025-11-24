import BaseComponent from "../base/BaseComponent.js";

export class SpectralSystemComponent extends BaseComponent {
    constructor(selectEl, descriptionEl) {
        super();
        this.selectEl = selectEl;
        this.descriptionEl = descriptionEl;
        this.onChange = null;
    }

    render({ systems, currentSystem }) {
        if (!this.selectEl) return;

        // Populate selector
        this.selectEl.innerHTML = '';
        systems.forEach((system, index) => {
            const option = document.createElement('option');
            option.textContent = system.name;
            option.value = index;
            if (system === currentSystem) option.selected = true;
            this.selectEl.appendChild(option);
        });

        // Update description
        this.updateContent(this.descriptionEl, currentSystem?.description || '', { asHTML: true });

        // Bind change event
        this.bindChange(this.selectEl, (val) => this.onChange(val));
    }
}