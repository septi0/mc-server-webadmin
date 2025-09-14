(function (bootstrap, McServerWebadmin) {

    const { createApp, api, notify, confirm, ws } = McServerWebadmin;
    const { Modal } = bootstrap;

    createApp({
        data: () => ({
            loaded: false,
            create_instance_modal: null,
            update_instance_modal: null,
            server_status: null,
            global_properties: {},
            instances: null,
            active_instance: null,
            create_instance_form: { properties: {} },
            update_instance_form: {},
            update_instance_ref: null,
            creating_instance: false,
            updating_instance: false,
            updating_server_status: false,
            updating_global_properties: false,
            activating_instance: false,
            stats_ws: null,
            stats_ws_unsubscribe: null,
        }),

        async created() {
            this.stats_ws = ws.getWebSocket("server/stats");

            try {
                await Promise.all([
                    this.fetchInstances(),
                    this.fetchGlobalProperties(),
                ]);
            } catch (error) {
                notify.error(`Error fetching initial data: ${error.message}`);
            } finally {
                this.loaded = true;
            }

            this.subscribeToServerStats();
        },

        async mounted() {
            this.create_instance_modal = new Modal(this.$refs.create_instance_modal);
            this.update_instance_modal = new Modal(this.$refs.update_instance_modal);
        },

        methods: {
            async startServer() {
                try {
                    this.updating_server_status = 'start';

                    const response = await api.startServer();

                    notify.success(response.message);
                } catch (error) {
                    notify.error(`Error starting server: ${error.message}`);
                } finally {
                    this.updating_server_status = false;
                }
            },

            async stopServer() {
                try {
                    this.updating_server_status = 'stop';

                    const response = await api.stopServer();

                    notify.success(response.message);
                } catch (error) {
                    notify.error(`Error stopping server: ${error.message}`);
                } finally {
                    this.updating_server_status = false;
                }
            },

            async restartServer() {
                try {
                    this.updating_server_status = 'restart';

                    const response = await api.restartServer();

                    notify.success(response.message);
                } catch (error) {
                    notify.error(`Error restarting server: ${error.message}`);
                } finally {
                    this.updating_server_status = false;
                }
            },

            async fetchInstances() {
                this.instances = await api.getInstances();

                this.active_instance = this.instances.find(i => i.active) || null;
            },

            async fetchGlobalProperties() {
                this.global_properties = await api.getGlobalProperties();
            },

            async subscribeToServerStats() {
                try {
                    this.stats_ws_unsubscribe = await this.stats_ws.subscribe((ev, data) => {
                        if (ev == 'message') {
                            this.server_status = data.status;
                        }
                    });
                } catch (err) {

                }
            },

            async createInstance() {
                try {
                    this.creating_instance = true;

                    const response = await api.createInstance(this.create_instance_form);

                    notify.success(response.message);

                    this.create_instance_modal.hide();

                    await this.fetchInstances();
                } catch (error) {
                    notify.error(`Error creating instance: ${error.message}`);
                } finally {
                    this.creating_instance = false;
                }
            },

            async updateInstance() {
                try {
                    this.updating_instance = true;
                    this.update_instance_ref.pending = true;

                    const response = await api.updateInstance(this.update_instance_form.id, this.update_instance_form);

                    notify.success(response.message);

                    this.update_instance_modal.hide();
                    this.setUpdateInstanceRef(null);

                    await this.fetchInstances();
                } catch (error) {
                    this.update_instance_ref.pending = false;

                    notify.error(`Error updating instance: ${error.message}`);
                } finally {
                    this.updating_instance = false;
                }
            },

            async activateInstance(instance) {
                if (!await confirm.show(`Are you sure you want to set instance ${instance.name} as active?`)) {
                    return;
                }

                try {
                    instance.pending = true;
                    this.activating_instance = true;

                    const response = await api.activateInstance(instance.id);

                    notify.success(response.message);

                    await this.fetchInstances();
                } catch (error) {
                    instance.pending = false;

                    notify.error(`Error activating instance: ${error.message}`);
                } finally {
                    this.activating_instance = false;
                }
            },

            async deleteInstance(instance) {
                if (!await confirm.show(`Are you sure you want to delete instance ${instance.name}?`)) {
                    return;
                }

                try {
                    instance.pending = true;

                    const response = await api.deleteInstance(instance.id);

                    notify.success(response.message);

                    await this.fetchInstances();
                } catch (error) {
                    instance.pending = false;

                    notify.error(error.message);
                }
            },

            async updateGlobalProperties() {
                try {
                    this.updating_global_properties = true;

                    const response = await api.updateGlobalProperties(this.global_properties);

                    notify.success(response.message);

                    await this.fetchGlobalProperties();
                } catch (error) {
                    notify.error(`Error updating global properties: ${error.message}`);
                } finally {
                    this.updating_global_properties = false;
                }
            },

            openCreateInstanceModal() {
                this.resetCreateInstanceModal();
                this.create_instance_modal.show();
            },

            openUpdateInstanceModal(instance) {
                this.setUpdateInstanceRef(instance);

                this.update_instance_form = {
                    id: instance.id,
                    name: instance.name,
                    server_version: instance.server_version,
                };

                this.update_instance_modal.show();
            },

            resetCreateInstanceModal() {
                this.create_instance_form = {
                    server_type: "vanilla",
                    properties: {
                        "level-type": "default",
                    },
                };

                this.$refs.world_file.value = null;
            },

            handleWorldFileUpload(e) {
                if (!e.target.files || e.target.files.length === 0) {
                    this.create_instance_form.world_archive = null;
                    return;
                }

                this.create_instance_form.world_archive = e.target.files[0];
                this.create_instance_form.properties = {}
            },

            setUpdateInstanceRef(instance) {
                this.update_instance_ref = instance;
            }

        }
    });

})(bootstrap, McServerWebadmin);
