(function (window, document, localStorage) {

    // setup sidebar interactivity
    const sidebar = document.getElementById('sidebar');
    const backdrop = document.getElementById('backdrop');
    const sidebar_btn = document.getElementById('btnSidebar');

    if (sidebar && backdrop && sidebar_btn) {

        const close = () => { sidebar.classList.remove('show'); backdrop.classList.remove('show'); };
        const open = () => { sidebar.classList.add('show'); backdrop.classList.add('show'); };

        sidebar_btn.addEventListener('click', open);
        backdrop.addEventListener('click', close);
    }

    // setup theme interactivity
    const root = document.documentElement;
    let theme = 'auto';

    try {
        theme = localStorage.getItem('theme') || 'auto';
    } catch (e) { }

    document.querySelectorAll('[data-theme-value]').forEach((btn) => {
        btn.addEventListener('click', () => {
            const v = btn.getAttribute('data-theme-value');

            try {
                localStorage.setItem('theme', v);
            } catch (e) { }

            theme = v;

            if (v === 'auto') {
                const prefers_dark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                root.setAttribute('data-bs-theme', prefers_dark ? 'dark' : 'light');
            } else {
                root.setAttribute('data-bs-theme', v);
            }
        });
    });

    if (theme === 'auto') {
        const mq = window.matchMedia('(prefers-color-scheme: dark)');
        mq.addEventListener('change', () => {
            if (theme === 'auto') {
                root.setAttribute('data-bs-theme', mq.matches ? 'dark' : 'light');
            }
        });
    }

})(window, document, localStorage);