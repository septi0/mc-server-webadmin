(function (bootstrap, window, McServerWebadmin) {

    const { createApp, api, notify, confirm } = McServerWebadmin;
    const { Modal } = bootstrap;

    createApp({
        data: () => ({
            loaded: false,
            world_id: null,
            world_datapacks: null,
            add_datapack_modal: null,
            add_datapack_form: {},
            adding_datapack: false,
        }),

        async created() {
            const path_parts = window.location.pathname.split('/');
            this.world_id = path_parts[path_parts.length - 2];

            try {
                await this.fetchWorldDatapacks();
            } catch (error) {
                notify.error(`Error fetching initial data: ${error.message}`);
            } finally {
                this.loaded = true;
            }
        },

        async mounted() {
            this.add_datapack_modal = new Modal(this.$refs.add_datapack_modal);
        },

        methods: {
            async fetchWorldDatapacks() {
                this.world_datapacks = await api.getWorldDatapacks(this.world_id);
            },

            async addDatapack() {
                try {
                    this.adding_datapack = true;

                    const response = await api.addWorldDatapack(this.world_id, this.add_datapack_form);

                    notify.success(response.message);

                    this.add_datapack_modal.hide();

                    await this.fetchWorldDatapacks();
                } catch (error) {
                    notify.error(`Error adding world datapack: ${error.message}`);
                } finally {
                    this.adding_datapack = false;
                }
            },

            async deleteDatapack(datapack) {
                if (! await confirm.show("Are you sure you want to delete this datapack? This action cannot be undone.")) {
                    return;
                }

                try {
                    datapack.pending = true;

                    const response = await api.deleteWorldDatapack(this.world_id, datapack.id);

                    notify.success(response.message);

                    await this.fetchWorldDatapacks();
                } catch (error) {
                    datapack.pending = false;

                    notify.error(error.message);
                }
            },

            openAddDatapackModal() {
                this.resetAddDatapackModal();
                this.add_datapack_modal.show();
            },

            handleDatapackFileUpload(e) {
                if (!e.target.files || e.target.files.length === 0) {
                    this.add_datapack_form.datapack_archive = null;
                    return;
                }

                this.add_datapack_form.datapack_archive = e.target.files[0];
            },

            resetAddDatapackModal() {
                this.add_datapack_form = {};
                this.$refs.datapack_file.value = null;
            },
        }
    });

})(bootstrap, window, McServerWebadmin);
