(function (bootstrap, window, McServerWebadmin) {

    const { createApp, api, notify, confirm } = McServerWebadmin;
    const { Modal } = bootstrap;

    createApp({
        data: () => ({
            loaded: false,
            instance_id: null,
            instance_mods: null,
            add_mod_modal: null,
            add_mod_form: {},
            adding_mod: false,
        }),

        async created() {
            const path_parts = window.location.pathname.split('/');
            this.instance_id = path_parts[path_parts.length - 2];

            try {
                await this.fetchInstanceMods();
            } catch (error) {
                notify.error(`Error fetching initial data: ${error.message}`);
            } finally {
                this.loaded = true;
            }
        },

        async mounted() {
            this.add_mod_modal = new Modal(this.$refs.add_mod_modal);
        },

        methods: {
            async fetchInstanceMods() {
                this.instance_mods = await api.getInstanceMods(this.instance_id);
            },

            async addMod() {
                try {
                    this.adding_mod = true;

                    const response = await api.addInstanceMod(this.instance_id, this.add_mod_form);

                    notify.success(response.message);

                    this.add_mod_modal.hide();

                    await this.fetchInstanceMods();
                } catch (error) {
                    notify.error(`Error adding instance mod: ${error.message}`);
                } finally {
                    this.adding_mod = false;
                }
            },

            async deleteMod(mod) {
                if (! await confirm.show("Are you sure you want to delete this mod? This action cannot be undone.")) {
                    return;
                }

                try {
                    mod.pending = true;

                    const response = await api.deleteInstanceMod(this.instance_id, mod.id);

                    notify.success(response.message);

                    await this.fetchInstanceMods();
                } catch (error) {
                    mod.pending = false;

                    notify.error(error.message);
                }
            },

            openAddModModal() {
                this.resetAddModModal();
                this.add_mod_modal.show();
            },

            handleModFileUpload(e) {
                if (!e.target.files || e.target.files.length === 0) {
                    this.add_mod_form.mod_jar = null;
                    return;
                }

                this.add_mod_form.mod_jar = e.target.files[0];
            },

            resetAddModModal() {
                this.add_mod_form = {};
                this.$refs.mod_file.value = null;
            },
        }
    });

})(bootstrap, window, McServerWebadmin);
