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
                    if (typeof value === 'object' && value.constructor == Object && value !== null) {
                        value = JSON.stringify(value);
                    }

                    if (value instanceof File) {
                        form.append(key, value, value.name);
                    } else {
                        console.log(value);
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

        async getWorlds() {
            return this.fetch("worlds");
        },

        async getActiveWorldInfo() {
            return this.fetch("worlds/active");
        },

        async createWorld(data) {
            return this.fetch("worlds", "POST", data);
        },

        async activateWorld(world_id) {
            return this.fetch(`worlds/${world_id}/activate`, "POST");
        },

        async updateWorld(world_id, data) {
            return this.fetch(`worlds/${world_id}`, "POST", data);
        },

        async deleteWorld(world_id) {
            return this.fetch(`worlds/${world_id}`, "DELETE");
        },

        async getGlobalProperties() {
            return this.fetch("global-properties");
        },

        async updateGlobalProperties(data) {
            return this.fetch("global-properties", "POST", data);
        },

        async getWorldBackups(world_id) {
            return this.fetch(`worlds/${world_id}/backups`);
        },

        async createWorldBackup(world_id) {
            return this.fetch(`worlds/${world_id}/backups`, "POST");
        },

        async restoreWorldBackup(world_id, backup_id) {
            return this.fetch(`worlds/${world_id}/backups/${backup_id}/restore`, "POST");
        },

        async deleteWorldBackup(world_id, backup_id) {
            return this.fetch(`worlds/${world_id}/backups/${backup_id}`, "DELETE");
        },

        async getWorldDatapacks(world_id) {
            return this.fetch(`worlds/${world_id}/datapacks`);
        },

        async addWorldDatapack(world_id, data) {
            return this.fetch(`worlds/${world_id}/datapacks`, "POST", data);
        },

        async deleteWorldDatapack(world_id, datapack_id) {
            return this.fetch(`worlds/${world_id}/datapacks/${datapack_id}`, "DELETE");
        },

        async getWorldMods(world_id) {
            return this.fetch(`worlds/${world_id}/mods`);
        },

        async addWorldMod(world_id, data) {
            return this.fetch(`worlds/${world_id}/mods`, "POST", data);
        },

        async deleteWorldMod(world_id, mod_id) {
            return this.fetch(`worlds/${world_id}/mods/${mod_id}`, "DELETE");
        },
        
    };

})(McServerWebadmin);