import { SpectralSystemActions } from './spectralSystemActions.js';
import { SpectralSystemComponent } from './SpectralSystemComponent.js';
import { AppState, spectralSystems } from '../../config.js';
import { smoothUpdateSystem } from '../../utils.js';

export class SpectralSystemController {
    constructor() {
        this.selectEl = document.getElementById('ratio-system-select');
        this.descriptionEl = document.getElementById('system-description');
        this.component = new SpectralSystemComponent(this.selectEl, this.descriptionEl);
    }

    init() {
        this.component.render(spectralSystems, AppState.currentSystem);
        
        this.component.onChange = (systemIndex) => {
            SpectralSystemActions.setSystem(systemIndex);
            smoothUpdateSystem(systemIndex);
        }

        this.selectEl.addEventListener('change', (e) => {
            const index = parseInt(e.target.value);
            SpectralSystemActions.setSystem(index);
        });
        document.addEventListener('spectral-system-changed', (e) => {
            this.component.render(spectralSystems, AppState.currentSystem);
        });
    }

    // For external use: update description only
    updateDescription() {
        this.descriptionEl.innerHTML = AppState.currentSystem?.description || '';
    }

    
}


