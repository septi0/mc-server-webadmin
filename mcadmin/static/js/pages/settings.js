(function (bootstrap, McServerWebadmin) {

    const { createApp, api, notify, confirm, ws } = McServerWebadmin;
    const { Modal } = bootstrap;

    createApp({
        data: () => ({
            loaded: false,
            create_world_modal: null,
            update_world_modal: null,
            server_status: null,
            global_properties: {},
            worlds: null,
            active_world: null,
            create_world: { properties: {} },
            update_world: {},
            update_world_ref: null,
            world_file: null,
            creating_world: false,
            updating_server_status: false,
            updating_global_properties: false,
            activating_world: false,
            stats_ws: null,
            stats_ws_unsubscribe: null,
        }),

        async created() {
            this.stats_ws = ws.getWebSocket("server/stats");

            try {
                await Promise.all([
                    this.fetchWorlds(),
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
            this.create_world_modal = new Modal(this.$refs.create_world_modal);
            this.update_world_modal = new Modal(this.$refs.update_world_modal);

            this.resetCreateWorldModal();
        },

        methods: {
            resetCreateWorldModal() {
                this.world_file = null;
                this.create_world = {
                    properties: {
                        "level-type": "default",
                    },
                };
            },

            openCreateWorldModal() {
                this.resetCreateWorldModal();
                this.create_world_modal.show();
            },

            openUpdateWorldModal(world) {
                this.update_world_ref = world;
                this.update_world = {
                    id: world.id,
                    name: world.name,
                    server_version: world.server_version,
                };

                this.update_world_modal.show();
            },

            handleWorldFileUpload(e) {
                if (!e.target.files || e.target.files.length === 0) {
                    this.world_file = null;
                    return;
                }

                this.world_file = e.target.files[0];
                this.create_world.properties = {}
            },

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

            async fetchWorlds() {
                this.worlds = await api.getWorlds();

                this.active_world = this.worlds.find(w => w.active) || null;
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

            async createWorld() {
                try {
                    this.creating_world = true;

                    const response = await api.createWorld(this.create_world, this.world_file);

                    notify.success(response.message);

                    this.create_world_modal.hide();
                    this.resetCreateWorldModal();

                    await this.fetchWorlds();
                } catch (error) {
                    notify.error(`Error creating world: ${error.message}`);
                } finally {
                    this.creating_world = false;
                }
            },

            async updateWorld() {
                try {
                    this.update_world_modal.hide();

                    this.update_world_ref.pending = true;

                    const response = await api.updateWorld(this.update_world.id, this.update_world);

                    notify.success(response.message);

                    this.update_world_modal.hide();
                    this.update_world_ref = null;

                    await this.fetchWorlds();
                } catch (error) {
                    this.update_world_ref.pending = false;

                    notify.error(`Error updating world: ${error.message}`);
                }
            },

            async activateWorld(world) {
                if (!await confirm.show(`Are you sure you want to set world ${world.name} as active?`)) {
                    return;
                }

                try {
                    world.pending = true;
                    this.activating_world = true;

                    const response = await api.activateWorld(world.id);

                    notify.success(response.message);

                    await this.fetchWorlds();
                } catch (error) {
                    world.pending = false;

                    notify.error(`Error activating world: ${error.message}`);
                } finally {
                    this.activating_world = false;
                }
            },

            async deleteWorld(world) {
                if (!await confirm.show(`Are you sure you want to delete world ${world.name}?`)) {
                    return;
                }

                try {
                    world.pending = true;

                    const response = await api.deleteWorld(world.id);

                    notify.success(response.message);

                    await this.fetchWorlds();
                } catch (error) {
                    world.pending = false;

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

            setUpdateWorldRef(world) {
                this.update_world_ref = world;
            }

        }
    });

})(bootstrap, McServerWebadmin);
