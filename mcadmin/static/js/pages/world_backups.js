(function (window, McServerWebadmin) {

    const { createApp, api, notify, confirm } = McServerWebadmin;

    createApp({
        data: () => ({
            loaded: false,
            world_id: null,
            world_backups: {},
            last_backup_dt: null,
            creating_backup: false,
        }),

        async created() {
            const path_parts = window.location.pathname.split('/');
            this.world_id = path_parts[path_parts.length - 2];

            try {
                await this.fetchWorldBackups();
            } catch (error) {
                notify.error(`Error fetching initial data: ${error.message}`);
            } finally {
                this.loaded = true;
            }
        },

        methods: {
            async fetchWorldBackups() {
                this.world_backups = await api.getWorldBackups(this.world_id);
                this.last_backup_dt = this.world_backups.length > 0 ? this.world_backups[0].created_at : null;
            },

            async createBackup() {
                if (! await confirm.show("You are about to create a new backup. This may take a while. Continue?")) {
                    return;
                }

                try {
                    this.creating_backup = true;

                    const response = await api.createWorldBackup(this.world_id);

                    notify.success(response.message);

                    await this.fetchWorldBackups();
                } catch (error) {
                    notify.error(`Error creating world backup: ${error.message}`);
                } finally {
                    this.creating_backup = false;
                }
            },

            async restoreBackup(backup) {
                if (! await confirm.show("Are you sure you want to restore this backup? This will overwrite the current world data.")) {
                    return;
                }

                try {
                    backup.pending = true;

                    const response = await api.restoreWorldBackup(this.world_id, backup.id);

                    notify.success(response.message);

                    await this.fetchWorldBackups();
                } catch (error) {
                    backup.pending = false;

                    notify.error(error.message);
                }
            },

            async deleteBackup(backup) {
                if (! await confirm.show("Are you sure you want to delete this backup? This action cannot be undone.")) {
                    return;
                }

                try {
                    backup.pending = true;

                    const response = await api.deleteWorldBackup(this.world_id, backup.id);

                    notify.success(response.message);

                    await this.fetchWorldBackups();
                } catch (error) {
                    backup.pending = false;

                    notify.error(error.message);
                }
            },
        }
    });

})(window, McServerWebadmin);
