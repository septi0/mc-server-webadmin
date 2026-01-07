(function (window, Vue, luxon) {

    const { createApp } = Vue;
    const { DateTime } = luxon;

    const app_config = JSON.parse(document.getElementById("app-data").textContent);

    window.McServerWebadmin = {};

    // app constants
    McServerWebadmin["API_URL"] = `${app_config.base_url}api/`;
    McServerWebadmin["WS_URL"] = `${app_config.base_url}ws/`;
    McServerWebadmin['STATS_POLLING_INTERVAL'] = 15000;

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

        app.config.globalProperties.$formatLocalDate = function (utc_datetime) {
            utc_datetime = utc_datetime.replace(" ", "T");
            return DateTime.fromISO(utc_datetime, { zone: "utc" }).toLocal().toLocaleString(DateTime.DATETIME_MED);
        };

        app.mount("#progressive-app");
    }

})(window, Vue, luxon);