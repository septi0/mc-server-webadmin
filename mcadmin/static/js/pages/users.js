(function (bootstrap, McServerWebadmin) {

    const { createApp, api, notify, confirm } = McServerWebadmin;
    const { Modal } = bootstrap;

    createApp({
        data: () => ({
            loaded: false,
            users: null,
            create_user_modal: null,
            update_user_modal: null,
            create_user_form: {},
            update_user_form: {},
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
        },

        methods: {
            async fetchUsers() {
                this.users = await api.getUsers();
            },

            async createUser() {
                try {
                    this.creating_user = true;

                    const response = await api.createUser(this.create_user_form);

                    notify.success(response.message);

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

                    const response = await api.updateUser(this.update_user_form.id, this.update_user_form);

                    notify.success(response.message);
                    this.setUpdateUserRef(null);

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

            openCreateUserModal() {
                this.resetCreateUserModal();
                this.create_user_modal.show();
            },

            openUpdateUserModal(user) {
                this.setUpdateUserRef(user);

                this.update_user_form = {
                    id: user.id,
                    username: user.username,
                    password: '',
                    role: user.role,
                };

                this.update_user_modal.show();
            },

            resetCreateUserModal() {
                this.create_user_form = {
                    role: 'user',
                };
            },

            setUpdateUserRef(user) {
                this.update_user_ref = user;
            },

        }
    });

})(bootstrap, McServerWebadmin);
