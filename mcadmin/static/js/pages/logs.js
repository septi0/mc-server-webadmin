(function (McServerWebadmin) {

    const { createApp, ws, notify } = McServerWebadmin;

    createApp({
        data: () => ({
            loaded: false,
            logs_ws: null,
            logs_ws_unsubscribe: null,
            follow_logs: true,
            connected: false,
            log_data: [],
            last_update: null,
        }),

        async created() {
            this.logs_ws = ws.getWebSocket("logs");

            try {
                await Promise.all([
                    this.subscribeToLogs(),
                ]);
            } catch (error) {
                notify.error(error.message);
            } finally {
                this.loaded = true;
            }
        },

        methods: {
            async clearLogs() {
                this.log_data = [];
                notify.success("Logs cleared");
            },

            async subscribeToLogs() {
                try {
                    this.logs_ws_unsubscribe = await this.logs_ws.subscribe((ev, data) => {
                        if (ev == 'connect') {
                            this.connected = true;
                        } else if (ev == 'disconnect') {
                            this.connected = false;
                        } else if (ev == 'message') {
                            if (this.follow_logs) {
                                this.log_data.push(data);
                                this.last_update = new Date().toISOString().slice(0, 19).replace("T", " ");

                                this.$nextTick(() => {
                                    this.$refs.log_view.scrollTop = this.$refs.log_view.scrollHeight;
                                });
                            }
                        }
                    });
                } catch (err) {
                    this.connected = false;
                }
            },
        },

        computed: {
            log_lines_count() {
                return this.log_data.length;
            }
        }
    });

})(McServerWebadmin);
