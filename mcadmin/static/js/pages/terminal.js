(function (Terminal, FitAddon, McServerWebadmin) {

    const { createApp, ws } = McServerWebadmin;

    createApp({
        data: () => ({
            loaded: false,
            term: null,
            fit_addon: null,
            terminal_ws: null,
            terminal_ws_unsubscribe: null,
            stats_ws: null,
            stats_ws_unsubscribe: null,
            server_status: null,
            connected: false,
            input: '',
            cmd_history: [''],
            cmd_history_index: -1,
        }),

        async created() {
            this.terminal_ws = ws.getWebSocket("terminal");
            this.stats_ws = ws.getWebSocket("server/stats");
            this.term = new Terminal({
                cursorBlink: true,
                fontSize: 16,
                scrollback: 2000,
            });
            this.fit_addon = new FitAddon.FitAddon();

            this.term.loadAddon(this.fit_addon);

            try {
                await this.subscribeToServerStats();
            } catch (error) {
                notify.error(error.message);
            } finally {
                this.loaded = true;
            }
        },

        async mounted() {
            this.term.open(this.$refs.terminal);
            this.fit_addon.fit();

            try {
                this.terminal_ws_unsubscribe = await this.terminal_ws.subscribe((ev, data) => {
                    if (ev == 'connect') {
                        this.connected = true;
                    } else if (ev == 'disconnect') {
                        this.connected = false;
                    } else if (ev == 'message') {
                        this.term.write(data.replace(/\r?\n/g, '\r\n'));
                        this.term.write('\r\n');
                        this.showPrompt();
                    }
                });

                this.term.write('\r\nSuccessfully connected. For help, type "help"\r\n');
                this.showPrompt();
            } catch (err) {
                this.term.write('\r\nError: Could not connect to terminal websocket\r\n');
                this.connected = false;

                throw err;
            }

            this.term.onData(this.handleTermInput);

            this.term.focus();
        },

        methods: {
            async subscribeToServerStats() {
                try {
                    this.stats_ws_unsubscribe = await this.stats_ws.subscribe((ev, data) => {
                        if (ev == 'message') {
                            this.server_status = data.status;
                        }
                    });
                } catch (err) {

                }
            },

            showPrompt() {
                this.term.write('> ');
            },

            handleTermInput(data) {
                if (!this.connected) {
                    this.term.write('\r\nError: Not connected to terminal\r\n');
                    return;
                }

                const cur_cmd_index = this.cmd_history.length - 1;

                // Enter
                if (data == "\r") {
                    const line = this.input;

                    if (line.trim()) {
                        this.input = '';
                        this.cmd_history.push('');
                        this.cmd_history_index = this.cmd_history.length - 1;

                        switch (line) {
                            case 'clear':
                                this.term.write('\r\n');
                                this.showPrompt();
                                this.term.clear();
                                break;
                            default:
                                this.terminal_ws.send(line);
                                this.term.write('\r\n');
                        }

                        this.input = '';
                    } else {
                        this.term.write('\r\n');
                        this.showPrompt();
                    }

                    return;
                }

                // Backspace
                if (data == "\x7f") {
                    if (this.input.length) {
                        this.input = this.input.slice(0, -1);
                        this.cmd_history[this.cmd_history_index] = this.input;
                        this.term.write('\b \b');
                    }

                    return;
                }

                // Up arrow
                if (data == "\x1B[A") {
                    if (this.cmd_history.length && this.cmd_history_index > 0) {
                        this.cmd_history_index--;
                        this.input = this.cmd_history[this.cmd_history_index];
                        this.term.write('\r\x1B[K');
                        this.showPrompt();
                        this.term.write(this.input);
                    }

                    return;
                }

                // Down arrow
                if (data == "\x1B[B") {
                    if (this.cmd_history.length && this.cmd_history_index < this.cmd_history.length - 1) {
                        this.cmd_history_index++;
                        this.input = this.cmd_history[this.cmd_history_index];
                        this.term.write('\r\x1B[K');
                        this.showPrompt();
                        this.term.write(this.input);
                    }

                    return;
                }

                // Ctrl + C
                if (data == "\x03") {
                    this.term.write('^C\r\n');
                    this.showPrompt();
                    return;
                }

                // filter out control characters
                if (data.match(/[\x00-\x1F\x7F]/)) {
                    return;
                }

                this.input += data;
                this.cmd_history[cur_cmd_index] = this.input;
                this.term.write(data);
            },
        },

    });

})(Terminal, FitAddon, McServerWebadmin);
