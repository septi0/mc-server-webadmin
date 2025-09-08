(function (McServerWebadmin, bootstrap) {
    const { Toast } = bootstrap;

    function renderNotification(type, message, options = {}) {
        const toast_types = { success: "success", error: "danger", info: "info" };

        const toast_el = document.createElement("div");
        toast_el.className = `toast align-items-center text-bg-${toast_types[type]} border-0`;
        toast_el.setAttribute("role", "alert");
        toast_el.setAttribute("aria-live", "assertive");
        toast_el.setAttribute("aria-atomic", "true");

        toast_el.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;

        document.getElementById('app-notifications').appendChild(toast_el);

        const notification = new Toast(toast_el, {
            autohide: options.autohide || true,
            delay: options.delay || 5000,
        });

        notification.show();

        toast_el.addEventListener('hidden.bs.toast', () => {
            toast_el.remove();
        }, { once: true });
    };

    McServerWebadmin["notify"] = {
        success(message, options) {
            renderNotification("success", message, options);
        },

        error(message, options) {
            console.error(message);
            renderNotification("error", message, options);
        },
    };

})(McServerWebadmin, bootstrap);