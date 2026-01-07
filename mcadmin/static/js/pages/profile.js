(function (McServerWebadmin) {

    const { createApp, api, notify, confirm } = McServerWebadmin;

    createApp({
        data: () => ({
            loaded: false,
            sessions: null,
            identities: null,
            password_form: { current_password: "" },
            updating_password: false,
        }),

        async created() {
            try {
                await Promise.all([
                    this.fetchSessions(),
                    this.fetchIdentities(),
                ]);
            } catch (error) {
                notify.error(`Error fetching user sessions: ${error.message}`);
            } finally {
                this.loaded = true;
            }
        },

        methods: {
            async fetchSessions() {
                this.sessions = await api.getUserSessions();
            },

            async fetchIdentities() {
                this.identities = await api.getUserIdentities();
            },

            async deleteSession(session) {
                if (!await confirm.show("Are you sure you want to delete this session?")) {
                    return;
                }

                try {
                    session.pending = true;

                    const response = await api.deleteUserSession(session.id);

                    notify.success(response.message);
                    await this.fetchSessions();
                } catch (error) {
                    session.pending = false;

                    notify.error(error.message);
                }
            },

            async deleteUserIdentity(identity) {
                if (!await confirm.show(`Are you sure you want to remove account identity ${identity.provider_name}? You won't be able to log in with this identity anymore.`)) {
                    return;
                }

                try {
                    identity.pending = true;

                    const response = await api.deleteUserIdentity(identity.id);

                    notify.success(response.message);
                    await this.fetchIdentities();
                } catch (error) {
                    identity.pending = false;

                    notify.error(error.message);
                }
            },

            async updatePassword() {
                try {
                    this.updating_password = true;

                    const response = await api.updateUserPassword(this.password_form);

                    notify.success(response.message);

                    this.password_form = { current_password: "" };
                } catch (error) {
                    notify.error(`Error updating password: ${error.message}`);
                } finally {
                    this.updating_password = false;
                }
            },

        }
    });

})(McServerWebadmin);
