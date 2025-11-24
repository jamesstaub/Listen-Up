// SpectralSystemComponent.js
// Handles rendering of the spectral system selector and description

export class SpectralSystemComponent {
    constructor(selectEl, descriptionEl) {
        this.selectEl = selectEl;
        this.descriptionEl = descriptionEl;
    }

    render(systems, currentSystem) {
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
        this.descriptionEl.innerHTML = currentSystem?.description || '';


        this.selectEl.addEventListener('change', this.handleSystemChange.bind(this));
    }

    handleSystemChange(e) {
        const systemIndex = parseInt(e.target.value);

        this.onChange?.(systemIndex);

        // update aria attribute
        e.target.setAttribute('aria-valuenow', systemIndex);
    }
}
