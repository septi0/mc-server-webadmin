(function (McServerWebadmin) {

    const { createApp, api, notify, confirm } = McServerWebadmin;

    createApp({
        data: () => ({
            loaded: false,
            sessions: null,
            password_form: {},
            updating_password: false,
        }),

        async created() {
            try {
                await this.fetchUserSessions();
            } catch (error) {
                notify.error(`Error fetching user sessions: ${error.message}`);
            } finally {
                this.loaded = true;
            }
        },

        methods: {
            async fetchUserSessions() {
                this.sessions = await api.getUserSessions();
            },

            async deleteSession(session) {
                if (!await confirm.show("Are you sure you want to delete this session?")) {
                    return;
                }

                try {
                    session.pending = true;

                    const response = await api.deleteUserSession(session.id);

                    notify.success(response.message);
                    await this.fetchUserSessions();
                } catch (error) {
                    session.pending = false;
                    
                    notify.error(error.message);
                }
            },

            async updatePassword() {
                try {
                    this.updating_password = true;

                    const response = await api.updateUserPassword(this.password_form);

                    notify.success(response.message);

                    this.password_form = {};
                } catch (error) {
                    notify.error(`Error updating password: ${error.message}`);
                } finally {
                    this.updating_password = false;
                }
            },

        }
    });

})(McServerWebadmin);
