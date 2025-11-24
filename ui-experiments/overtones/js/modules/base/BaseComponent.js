// BaseComponent.js
export default class BaseComponent {
    constructor() {}

    render() {
        // Override in derived class
        throw new Error('render() must be implemented in the derived component');
    }

    /**
     * Generic content updater: text or HTML
     * @param {HTMLElement} el
     * @param {string} content
     * @param {object} options
     */
    updateContent(el, content = '', { asHTML = false } = {}) {
        if (!el) return;
        if (asHTML) el.innerHTML = content;
        else el.textContent = content;
    }

    /**
     * Bind a change event to any input/select element
     * 
     * DEPRECATED: Use bindEvent instead
     */
    bindChange(el, handler) {
        if (!el) return;
        el.addEventListener('change', (e) => {
            const value = parseInt(e.target.value);
            handler?.(value);
            e.target.setAttribute('aria-valuenow', value);
        });
    }

    /**
     * Helper to bind events and auto-preserve `this`
     * @param {HTMLElement} el
     * @param {string} event
     * @param {Function} handler
     */
    bindEvent(el, event, handler) {
        if (!el) return;
        el.addEventListener(event, handler.bind(this));
    }
}
