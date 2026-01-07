(function (McServerWebadmin) {

    McServerWebadmin["api"] = {
        async fetch(url, request_method = 'GET', data = {}, headers = {}) {
            let options = {
                method: request_method,
                headers: headers,
            };

            if (request_method == 'POST') {
                const form = new FormData();

                for (let [key, value] of Object.entries(data)) {
                    if (typeof value === 'object' && (value.constructor == Object || value instanceof Array) && value !== null) {
                        value = JSON.stringify(value);
                    }

                    if (value instanceof File) {
                        form.append(key, value, value.name);
                    } else {
                        form.append(key, value);
                    }
                }

                options.body = form;
            }

            const response = await fetch(`${McServerWebadmin["API_URL"]}${url}`, options);
            const response_data = await response.json();

            if (!response_data && !response.ok) {
                throw new Error("Failed to fetch data");
            }

            if (response_data.status && response_data.status === "error") {
                throw new Error(response_data.message);
            }

            return response_data;
        },

        async getServerStatus() {
            return this.fetch("server/status");
        },

        async getServerInfo() {
            return this.fetch("server/info");
        },

        async startServer() {
            return this.fetch("server/start", "POST");
        },

        async stopServer() {
            return this.fetch("server/stop", "POST");
        },

        async restartServer() {
            return this.fetch("server/restart", "POST");
        },

        async getUserSessions() {
            return this.fetch("self/sessions");
        },

        async updateUserPassword(data) {
            return this.fetch("self/update", "POST", data);
        },

        async deleteUserSession(session_id) {
            return this.fetch(`self/sessions/${session_id}`, "DELETE");
        },

        async getUsers() {
            return this.fetch("admin/users");
        },

        async createUser(data) {
            return this.fetch("admin/users", "POST", data);
        },

        async updateUser(user_id, data) {
            const updated_data = { ...data };
            if (!updated_data.password) {
                delete updated_data.password;
            }

            return this.fetch(`admin/users/${user_id}`, "POST", updated_data);
        },

        async deleteUser(user_id) {
            return this.fetch(`admin/users/${user_id}`, "DELETE");
        },

        async getInstances() {
            return this.fetch("instances");
        },

        async getActiveInstanceInfo() {
            return this.fetch("instances/active");
        },

        async createInstance(data) {
            return this.fetch("instances", "POST", data);
        },

        async activateInstance(instance_id) {
            return this.fetch(`instances/${instance_id}/activate`, "POST");
        },

        async updateInstance(instance_id, data) {
            return this.fetch(`instances/${instance_id}`, "POST", data);
        },

        async deleteInstance(instance_id) {
            return this.fetch(`instances/${instance_id}`, "DELETE");
        },

        async getGlobalProperties() {
            return this.fetch("global-properties");
        },

        async updateGlobalProperties(data) {
            return this.fetch("global-properties", "POST", data);
        },

        async getInstanceBackups(instance_id) {
            return this.fetch(`instances/${instance_id}/backups`);
        },

        async createInstanceBackup(instance_id) {
            return this.fetch(`instances/${instance_id}/backups`, "POST");
        },

        async restoreInstanceBackup(instance_id, backup_id) {
            return this.fetch(`instances/${instance_id}/backups/${backup_id}/restore`, "POST");
        },

        async deleteInstanceBackup(instance_id, backup_id) {
            return this.fetch(`instances/${instance_id}/backups/${backup_id}`, "DELETE");
        },

        async getInstanceDatapacks(instance_id) {
            return this.fetch(`instances/${instance_id}/datapacks`);
        },

        async addInstanceDatapack(instance_id, data) {
            return this.fetch(`instances/${instance_id}/datapacks`, "POST", data);
        },

        async updateInstanceDatapack(instance_id, datapack_id, data) {
            return this.fetch(`instances/${instance_id}/datapacks/${datapack_id}`, "POST", data);
        },

        async deleteInstanceDatapack(instance_id, datapack_id) {
            return this.fetch(`instances/${instance_id}/datapacks/${datapack_id}`, "DELETE");
        },

        async getInstanceMods(instance_id) {
            return this.fetch(`instances/${instance_id}/mods`);
        },

        async addInstanceMod(instance_id, data) {
            return this.fetch(`instances/${instance_id}/mods`, "POST", data);
        },

        async updateInstanceMod(instance_id, mod_id, data) {
            return this.fetch(`instances/${instance_id}/mods/${mod_id}`, "POST", data);
        },

        async deleteInstanceMod(instance_id, mod_id) {
            return this.fetch(`instances/${instance_id}/mods/${mod_id}`, "DELETE");
        },

        async getAuthMethods() {
            return this.fetch("admin/auth_config/methods");
        },

        async getOIDCProviders() {
            return this.fetch("admin/auth_config/oidc-providers");
        },

        async updateAuthMethods(data) {
            return this.fetch("admin/auth_config/methods", "POST", data);
        },

        async createOIDCProvider(data) {
            return this.fetch("admin/auth_config/oidc-providers", "POST", data);
        },

        async updateOIDCProvider(provider_id, data) {
            return this.fetch(`admin/auth_config/oidc-providers/${provider_id}`, "POST", data);
        },

        async deleteOIDCProvider(provider_id) {
            return this.fetch(`admin/auth_config/oidc-providers/${provider_id}`, "DELETE");
        },

        async getUserIdentities() {
            return this.fetch("self/identities");
        },

        async deleteUserIdentity(identity_id) {
            return this.fetch(`self/identities/${identity_id}`, "DELETE");
        }

    };

})(McServerWebadmin);