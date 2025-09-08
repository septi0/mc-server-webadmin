(function (document, McServerWebadmin, bootstrap) {
    const { Modal } = bootstrap;

    async function renderConfirmModal(message, options = {}) {
        const modal_el = document.createElement("div");
        modal_el.className = "modal fade";
        modal_el.setAttribute("tabindex", "-1");
        modal_el.setAttribute("aria-labelledby", "confirmModalLabel");
        modal_el.setAttribute("aria-hidden", "true");

        modal_el.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="confirmModalLabel">Confirm</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <p>${message}</p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" id="confirm-ok-btn" class="btn btn-primary">Confirm</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal_el);

        const modal = new Modal(modal_el);
        modal.show();

        return new Promise((resolve) => {
            let confirmed = false;

            document.getElementById('confirm-ok-btn').addEventListener('click', (e) => {
                confirmed = true;
                modal.hide();
            }, { once: true });

            modal_el.addEventListener("hidden.bs.modal", (e) => {
                modal.dispose();
                modal_el.remove();

                resolve(confirmed);
            }, { once: true });
        });
    };

    McServerWebadmin["confirm"] = {
        async show(message, options) {
            return await renderConfirmModal(message, options);
        }
    };

})(document, McServerWebadmin, bootstrap);