(function (window, Vue) {

    const { createApp } = Vue;
    const components = [];
    const properties = [];

    window.McServerWebadmin = {};

    // app constants
    McServerWebadmin["API_URL"] = "/api/";
    McServerWebadmin["WS_URL"] = "/ws/";
    McServerWebadmin['STATS_POLLING_INTERVAL'] = 30000;

    // app functions
    McServerWebadmin['registerComponent'] = function (name, component) {
        components.push({ name, component });
    };

    McServerWebadmin['registerProperty'] = function (name, value) {
        properties.push({ name, value });
    };

    McServerWebadmin['createApp'] = function (options) {
        const app = createApp(options);

        app.directive('text-ng', {
            beforeMount(el, binding) {
                el.textContent = binding.value == null ? '' : String(binding.value)
            },
            updated(el, binding) {
                if (binding.value !== binding.oldValue) {
                    el.textContent = binding.value == null ? '' : String(binding.value)
                }
            },
        });

        components.forEach(({ name, component }) => {
            app.component(name, component);
        });

        properties.forEach(({ name, value }) => {
            app.config.globalProperties[name] = value;
        });

        app.mount("#enhanced-app");
    }

})(window, Vue);