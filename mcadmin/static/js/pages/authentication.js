(function (bootstrap, McServerWebadmin) {

    const { createApp, api, notify, confirm } = McServerWebadmin;
    const { Modal } = bootstrap;

    createApp({
        data: () => ({
            loaded: false,
            auth_methods: {},
            oidc_providers: [],
            create_oidc_provider_modal: null,
            update_oidc_provider_modal: null,
            updating_auth_methods: false,
            show_oidc_card: false,
            create_oidc_provider_form: {config: {}},
            update_oidc_provider_form: {config: {}},
            creating_oidc_provider: false,
            updating_oidc_provider: false,
        }),

        async created() {
            try {
                await Promise.all([
                    this.fetchAuthMethods(),
                    this.fetchOIDCProviders(),
                ]);

            } catch (error) {
                notify.error(`Error fetching authentication methods: ${error.message}`);
            } finally {
                this.loaded = true;
            }

            this.resetCreateOIDCProviderForm();
        },

        async mounted() {
            this.create_oidc_provider_modal = new Modal(this.$refs.create_oidc_provider_modal);
            this.update_oidc_provider_modal = new Modal(this.$refs.update_oidc_provider_modal);
        },

        methods: {
            async fetchAuthMethods() {
                this.auth_methods = await api.getAuthMethods();

                if (this.auth_methods && this.auth_methods.includes("oidc")) this.show_oidc_card = true;
                else this.show_oidc_card = false;
            },

            async fetchOIDCProviders() {
                this.oidc_providers = await api.getOIDCProviders();
            },

            async updateAuthMethods() {
                try {
                    this.updating_auth_methods = true;

                    const response = await api.updateAuthMethods({ auth_methods: [...this.auth_methods] });

                    notify.success(response.message);

                    await this.fetchAuthMethods();
                } catch (error) {
                    this.updating_auth_methods = false;

                    notify.error(error.message);
                } finally {
                    this.updating_auth_methods = false;
                }
            },

            async createOIDCProvider() {
                try {
                    this.creating_oidc_provider = true;

                    const response = await api.createOIDCProvider(this.create_oidc_provider_form);

                    notify.success(response.message);

                    this.create_oidc_provider_modal.hide();

                    await this.fetchOIDCProviders();
                } catch (error) {
                    notify.error(error.message);
                } finally {
                    this.creating_oidc_provider = false;
                }
            },

            async updateOIDCProvider() {
                try {
                    this.updating_oidc_provider = true;
                    this.update_oidc_provider_ref.pending = true;

                    const response = await api.updateOIDCProvider(this.update_oidc_provider_form.id, this.update_oidc_provider_form);

                    notify.success(response.message);

                    this.update_oidc_provider_modal.hide();
                    this.setUpdateOIDCProviderRef(null);

                    await this.fetchOIDCProviders();
                } catch (error) {
                    this.update_oidc_provider_ref.pending = false;

                    notify.error(error.message);
                } finally {
                    this.updating_oidc_provider = false;
                }
            },

            async deleteOIDCProvider(provider) {
                if (!await confirm.show(`Are you sure you want to delete provider ${provider.name}?`)) {
                    return;
                }

                try {
                    provider.pending = true;

                    const response = await api.deleteOIDCProvider(provider.id);

                    notify.success(response.message);
                    await this.fetchOIDCProviders();
                } catch (error) {
                    provider.pending = false;

                    notify.error(error.message);
                }
            },

            openCreateOIDCProviderModal() {
                this.resetCreateOIDCProviderForm();

                this.create_oidc_provider_modal.show();
            },

            openUpdateOIDCProviderModal(provider) {
                this.setUpdateOIDCProviderRef(provider);
                this.setUpdateOIDCProviderForm(provider);

                this.update_oidc_provider_modal.show();
            },

            resetCreateOIDCProviderForm() {
                this.create_oidc_provider_form = {
                    config: {
                        scope: "openid profile",
                        user_claim: "preferred_username",
                    },
                };
            },

            setUpdateOIDCProviderRef(provider) {
                this.update_oidc_provider_ref = provider;
            },

            setUpdateOIDCProviderForm(provider) {
                this.update_oidc_provider_form = {
                    id: provider.id,
                    name: provider.name,
                    default: provider.default,
                    allow_registration: provider.allow_registration,
                    auto_launch: provider.auto_launch,
                    user_claim: provider.user_claim,
                    config: provider.config,
                };
            },

        }
    });

})(bootstrap, McServerWebadmin);
