(function (window, McServerWebadmin) {

    const { createApp, api, notify, confirm } = McServerWebadmin;

    createApp({
        data: () => ({
            loaded: false,
            instance_id: null,
            instance_backups: null,
            last_backup_dt: null,
            creating_backup: false,
        }),

        async created() {
            const path_parts = window.location.pathname.split('/');
            this.instance_id = path_parts[path_parts.length - 2];

            try {
                await this.fetchInstanceBackups();
            } catch (error) {
                notify.error(`Error fetching initial data: ${error.message}`);
            } finally {
                this.loaded = true;
            }
        },

        methods: {
            async fetchInstanceBackups() {
                this.instance_backups = await api.getInstanceBackups(this.instance_id);
                this.last_backup_dt = this.instance_backups.length > 0 ? this.instance_backups[0].created_at : null;
            },

            async createBackup() {
                if (! await confirm.show("You are about to create a new backup. This may take a while. Continue?")) {
                    return;
                }

                try {
                    this.creating_backup = true;

                    const response = await api.createInstanceBackup(this.instance_id);

                    notify.success(response.message);

                    await this.fetchInstanceBackups();
                } catch (error) {
                    notify.error(`Error creating instance backup: ${error.message}`);
                } finally {
                    this.creating_backup = false;
                }
            },

            async restoreBackup(backup) {
                if (! await confirm.show("Are you sure you want to restore this backup? This will overwrite the current instance data.")) {
                    return;
                }

                try {
                    backup.pending = true;

                    const response = await api.restoreInstanceBackup(this.instance_id, backup.id);

                    notify.success(response.message);

                    await this.fetchInstanceBackups();
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

                    const response = await api.deleteInstanceBackup(this.instance_id, backup.id);

                    notify.success(response.message);

                    await this.fetchInstanceBackups();
                } catch (error) {
                    backup.pending = false;

                    notify.error(error.message);
                }
            },
        }
    });

})(window, McServerWebadmin);
