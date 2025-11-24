export class BaseController {
    constructor() {
        if (!this.createComponent) {
            throw new Error("Subclass must implement createComponent()");
        }

        // Subclass builds and returns the component instance
        this.component = this.createComponent();
    }

    /**
     * Initializes the controller lifecycle.
     * Call this after construction.
     */
    init() {
        this.update();
        this.bindComponentEvents();
        this.bindExternalEvents();
    }

    /**
     * Subclass must provide props derived from AppState.
     */
    getProps() {
        throw new Error("Subclass must implement getProps()");
    }

    /**
     * Render the component using derived props.
     */
    update() {
        const props = this.getProps();
        this.component.render(props);
    }

    /**
     * Override to listen to component-level events like:
     * this.component.onChange = (v) => {}
     */
    bindComponentEvents() {}

    /**
     * Override to listen for global or DOM events:
     * document.addEventListener("...", this.update.bind(this))
     */
    bindExternalEvents() {}

    /**
     * Optional cleanup method for future use
     */
    destroy() {
        // Subclass may override for teardown
    }
}
