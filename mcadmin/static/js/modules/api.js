(function (McServerWebadmin) {

    McServerWebadmin["api"] = {
        async fetch(url, request_method = 'GET', data = {}, file = null, headers = {}) {
            let options = {
                method: request_method,
                headers: headers,
            };

            if (request_method == 'POST') {
                const form = new FormData();

                for (let [key, value] of Object.entries(data)) {
                    if (typeof value === 'object' && value !== null) {
                        value = JSON.stringify(value);
                    }

                    form.append(key, value);
                }

                if (file) {
                    form.append("file", file, file.name);
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
            return this.fetch("profile/sessions");
        },

        async updateUserPassword(data) {
            return this.fetch("profile/password-update", "POST", data);
        },

        async deleteUserSession(session_id) {
            return this.fetch("profile/session-delete", "POST", { session_id: session_id });
        },

        async getUsers() {
            return this.fetch("admin/users");
        },

        async createUser(data) {
            return this.fetch("admin/user-create", "POST", data);
        },

        async updateUser(data) {
            const updated_data = { ...data };
            if (!updated_data.password) {
                delete updated_data.password;
            }

            return this.fetch("admin/user-update", "POST", updated_data);
        },

        async deleteUser(user_id) {
            return this.fetch("admin/user-delete", "POST", { id: user_id });
        },

        async getWorlds() {
            return this.fetch("server/worlds");
        },

        async getActiveWorldInfo() {
            return this.fetch("server/active-world");
        },

        async createWorld(data, file = null) {
            return this.fetch("server/world-create", "POST", data, file);
        },

        async activateWorld(world_id) {
            return this.fetch("server/world-activate", "POST", { id: world_id });
        },

        async updateWorld(data) {
            return this.fetch("server/world-update", "POST", data);
        },

        async deleteWorld(world_id) {
            return this.fetch("server/world-delete", "POST", { id: world_id });
        },

        async getGlobalProperties() {
            return this.fetch("server/global-properties");
        },

        async updateGlobalProperties(data) {
            return this.fetch("server/global-properties", "POST", data);
        },
        
    };

})(McServerWebadmin);