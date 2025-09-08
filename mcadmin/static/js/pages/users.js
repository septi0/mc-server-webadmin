(function (bootstrap, McServerWebadmin) {

    const { createApp, api, notify, confirm } = McServerWebadmin;
    const { Modal } = bootstrap;

    createApp({
        data: () => ({
            loaded: false,
            users: null,
            create_user_modal: null,
            update_user_modal: null,
            create_user: {},
            update_user: {},
            update_user_ref: null,
            creating_user: false,
        }),

        async created() {
            try {
                await this.fetchUsers();
            } catch (error) {
                notify.error(`Error fetching users: ${error.message}`);
            } finally {
                this.loaded = true;
            }
        },

        async mounted() {
            this.create_user_modal = new Modal(this.$refs.create_user_modal);
            this.update_user_modal = new Modal(this.$refs.update_user_modal);

            this.resetCreateUserModal();
        },

        methods: {
            resetCreateUserModal() {
                this.create_user = {
                    role: 'user',
                };
            },

            openCreateUserModal() {
                this.resetCreateUserModal();
                this.create_user_modal.show();
            },

            openUpdateUserModal(user) {
                this.update_user_ref = user;
                this.update_user = {
                    id: user.id,
                    username: user.username,
                    password: '',
                    role: user.role,
                };

                this.update_user_modal.show();
            },

            async fetchUsers() {
                this.users = await api.getUsers();
            },

            async createUser() {
                try {
                    this.creating_user = true;
                    
                    const response = await api.createUser(this.create_user);

                    notify.success(response.message);

                    this.resetCreateUserModal();
                    this.create_user_modal.hide();

                    await this.fetchUsers();
                } catch (error) {
                    notify.error(error.message);
                } finally {
                    this.creating_user = false;
                }
            },

            async updateUser() {
                try {
                    this.update_user_modal.hide();

                    this.update_user_ref.pending = true;

                    const response = await api.updateUser(this.update_user);

                    notify.success(response.message);

                   

                    await this.fetchUsers();
                } catch (error) {
                    this.update_user_ref.pending = false;
                    
                    notify.error(error.message);
                }
            },

            async deleteUser(user) {
                if (!await confirm.show(`Are you sure you want to delete user ${user.username}?`)) {
                    return;
                }

                try {
                    user.pending = true;
                    
                    const response = await api.deleteUser(user.id);

                    notify.success(response.message);
                    await this.fetchUsers();
                } catch (error) {
                    user.pending = false;

                    notify.error(error.message);
                }
            },

        }
    });

})(bootstrap, McServerWebadmin);
