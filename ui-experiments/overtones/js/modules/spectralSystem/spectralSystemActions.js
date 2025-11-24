// spectralSystemActions.js
// Pure state mutation and event dispatch for spectral system changes

import { AppState, spectralSystems, updateAppState } from '../../config.js';
import { UIStateManager } from '../../UIStateManager.js';

export const SpectralSystemActions = {
    setSystem(index) {
        updateAppState({ currentSystem: spectralSystems[index] });

        // Resize amplitudes to match new system
        const numPartials = AppState.currentSystem.ratios.length;
        const oldAmps = AppState.harmonicAmplitudes || [];
        const newAmps = [];
        for (let i = 0; i < numPartials; i++) {
            newAmps[i] = typeof oldAmps[i] === 'number' ? oldAmps[i] : (i === 0 ? 1.0 : 0.0);
        }
        for (let i = oldAmps.length; i < numPartials; i++) {
            newAmps[i] = (i === 0 ? 1.0 : 0.0);
        }
        AppState.harmonicAmplitudes = newAmps;
        document.dispatchEvent(new CustomEvent('spectral-system-changed', {
            detail: { index, system: AppState.currentSystem }
        }));
    }

};
