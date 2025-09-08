(function (McServerWebadmin, WebSocket) {

    class WsProxy {
        constructor(url) {
            this.url = url;
            this.socket = null;

            this.reconnect = true;
            this.backoff_ms = 500;
            this.max_backoff_ms = 10000;
            this.max_retries = 20;

            this.retries = 0;
            this._subs = new Set();
            this._queue = [];
            this._timer = null;
        }

        async connect() {
            if (this.socket) {
                await this._waitOpen();
                return this.socket;
            }

            this.socket = new WebSocket(this.url);

            const s = this.socket;

            s.addEventListener("open", () => {
                console.log("WebSocket connected:", this.url);

                this.retries = 0;
                this._flushQueue();

                for (const fn of this._subs) {
                    try { fn('connect', null); } catch (err) { console.error("WS subscriber error:", err); }
                }
            });

            s.addEventListener("message", (e) => {
                let data = e.data;
                try { data = JSON.parse(e.data); } catch { /* keep as string */ }

                for (const fn of this._subs) {
                    try { fn('message', data); } catch (err) { console.error("WS subscriber error:", err); }
                }
            });

            s.addEventListener("close", () => {
                console.log("WebSocket disconnected:", this.url);
                
                if (this.reconnect) this._scheduleReconnect();

                for (const fn of this._subs) {
                    try { fn('disconnect', null); } catch (err) { console.error("WS subscriber error:", err); }
                }
            });

            s.addEventListener("error", (err) => {
                console.error("WebSocket error:", err);
            });

            await this._waitOpen();

            return s;
        }

        async subscribe(handler) {
            await this.connect();

            this._subs.add(handler);

            try { handler('connect', null); } catch (err) { console.error("WS subscriber error:", err); }

            return () => this._subs.delete(handler);
        }

        async send(payload) {
            await this.connect();

            const msg = (typeof payload === "string") ? payload : JSON.stringify(payload);

            if (this.socket.readyState === WebSocket.OPEN) {
                this.socket.send(msg);
            } else {
                this._queue.push(msg);
            }
        }

        close() {
            this.reconnect = false;

            clearTimeout(this._timer);

            if (this.socket && this.socket.readyState !== WebSocket.CLOSED) {
                try { this.socket.close(); } catch { }
                this.socket = null;
            }
        }

        _flushQueue() {
            while (this._queue.length) {
                this.socket.send(this._queue.shift());
            }
        }

        async _waitOpen() {
            const s = this.socket;

            if (!s) throw new Error("Socket not created");

            if (s.readyState === WebSocket.OPEN) return;
            if (s.readyState === WebSocket.CLOSED) throw new Error("Socket closed before open");

            await new Promise((resolve, reject) => {
                const ws_open = () => { cleanup(); resolve(); };
                const ws_err = (e) => { cleanup(); reject(new Error("WebSocket connection error")); };
                const ws_close = () => { cleanup(); reject(new Error("Socket closed during connect")); };
                const cleanup = () => {
                    s.removeEventListener("open", ws_open);
                    s.removeEventListener("error", ws_err);
                    s.removeEventListener("close", ws_close);
                };

                s.addEventListener("open", ws_open, { once: true });
                s.addEventListener("error", ws_err, { once: true });
                s.addEventListener("close", ws_close, { once: true });
            });
        }

        _scheduleReconnect() {
            clearTimeout(this._timer);

            if (this.retries >= this.max_retries) {
                console.error(`Max WebSocket reconnection attempts reached (${this.max_retries}). Giving up.`);
                return;
            }

            this.retries += 1;
            const delay = Math.min(this.backoff_ms * Math.pow(2, this.retries - 1), this.max_backoff_ms);
            this._timer = setTimeout(() => {
                this.socket = null;
                this.connect().catch(() => { /* next close/error will reschedule */ });
            }, delay);

            console.warn(`WebSocket reconnecting in ${delay}ms (retry #${this.retries})`);
        }
    }

    McServerWebadmin.ws = {
        _map: Object.create(null),

        getWebSocket(url, opts) {
            if (!this._map[url]) {
                const full_url = `${McServerWebadmin["WS_URL"]}${url}`;
                this._map[url] = new WsProxy(full_url, opts);
            }

            return this._map[url];
        },

        close(url) {
            const inst = this._map[url];
            if (inst) {
                inst.close();
                delete this._map[url];
            }
        }
    };

})(McServerWebadmin, WebSocket);
