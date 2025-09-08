(function (luxon, McServerWebadmin) {

    const { createApp, api, notify, ws } = McServerWebadmin;
    const { DateTime } = luxon;

    createApp({
        data: () => ({
            loaded: false,
            server_stats: {},
            server_info: {},
            world_info: {},
            updating_server_status: false,
            uptime: null,
            uptime_interval: null,
            stats_ws: null,
            stats_ws_unsubscribe: null,
        }),

        async created() {
            this.stats_ws = ws.getWebSocket("stats");

            try {
                await Promise.all([
                    this.fetchServerInfo(),
                    this.fetchActiveWorldInfo(),
                    this.subscribeToServerStats(),
                ]);
            } catch (error) {
                notify.error(error.message);
            } finally {
                this.loaded = true;
            }
        },

        methods: {
            async fetchServerInfo() {
                this.server_info = await api.getServerInfo();

                if (this.server_info) {
                    if (this.server_info.host) {
                        this.server_info.ip_display = this.server_info.host + ' (' + this.server_info.ip + ')';
                    } else {
                        this.server_info.ip_display = this.server_info.ip;
                    }
                }
            },

            async fetchActiveWorldInfo() {
                this.world_info = await api.getActiveWorldInfo();
            },

            async subscribeToServerStats() {
                try {
                    this.stats_ws_unsubscribe = await this.stats_ws.subscribe((ev, data) => {
                        if (ev == 'message') {
                            this.server_stats = data;

                            this.startUptimeTimer(this.server_stats.started_at);
                        }
                    });
                } catch (err) {

                }
            },

            async startServer() {
                try {
                    this.updating_server_status = 'start';

                    const response = await api.startServer();

                    notify.success(response.message);
                } catch (error) {
                    notify.error(`Error starting server: ${error.message}`);
                } finally {
                    this.updating_server_status = false;
                }
            },

            async stopServer() {
                try {
                    this.updating_server_status = 'stop';

                    const response = await api.stopServer();

                    notify.success(response.message);
                } catch (error) {
                    notify.error(`Error stopping server: ${error.message}`);
                } finally {
                    this.updating_server_status = false;
                }
            },

            async startUptimeTimer(utc_datetime) {
                if (this.uptime_interval) {
                    clearInterval(this.uptime_interval);
                    this.uptime_interval = null;
                }

                if (!utc_datetime) {
                    this.uptime = null;
                    return;
                }

                utc_datetime = utc_datetime.replace(" ", "T");
                const dt = DateTime.fromISO(utc_datetime, { zone: "utc" });

                this.uptime_interval = setInterval(() => {
                    let duration = DateTime.utc().diff(dt).shiftTo('hours', 'minutes', 'seconds');
                    this.uptime = duration.toFormat("h'h, 'm'm, 's's'", { floor: true });
                });
            },
        }
    });

})(luxon, McServerWebadmin);
