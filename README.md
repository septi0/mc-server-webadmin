# Minecraft Server WebAdmin

A modern web-based admin panel for managing Minecraft servers, worlds, and player options built with Python.

## Features

- Start, stop, and restart Minecraft servers from the web UI
- Manage multiple worlds: create, activate, and delete worlds
- Change server version and configuration
- Player options: difficulty, gamemode, whitelist, MOTD, and more
- User authentication and role-based access
- View server logs and terminal output
- Responsive, mobile-friendly interface

## Quick Start (Docker)

### 1. Deploy container

Docker run command:
```bash
docker run -d \
	-e MCADMIN_DISPLAY_IP=your.public.ip.address \
	-p 8000:8000 \
	-p 25565:25565 \
	-v $(pwd)/data:/data \
	ghcr.io/septi0/mc-server-webadmin:latest
```

OR

Docker compose file:

```yaml
services:
  mc-server-webadmin:
    image: ghcr.io/septi0/mc-server-webadmin:latest
    environment:
      - MCADMIN_DISPLAY_IP=your.public.ip.address
    ports:
      - "8000:8000"
      - "25565:25565"
    volumes:
      - ./data:/data
```

### 2. Configure

Configuration is done via environment variables. Any entry from the config file has it's equivalent as an environment variable, with the format `MCADMIN_<KEY>` for minecraft server related configuration and `MCADMIN_WEB_<KEY>` for web server related configuration.

Common configuration options:

- `MCADMIN_JAVA_MIN_MEMORY`: The minimum amount of memory to allocate to the Java process (default: `1G`)
- `MCADMIN_JAVA_MAX_MEMORY`: The maximum amount of memory to allocate to the Java process (default: `1G`)
- `MCADMIN_WEB_TRUSTED_PROXIES`: Comma-separated list of trusted proxy IPs
- `MCADMIN_DISPLAY_IP`: The IP address to display for connecting to the Minecraft server

**Note!** When running the application as a container (or using proxies / port forwarding, etc.), the real IP and port are not directly accessible to the app and it won't display the correct connect information. To fix this, use `MCADMIN_DISPLAY_IP` (or `MCADMIN_DISPLAY_HOST`), and `MCADMIN_DISPLAY_PORT` configuration options.

For details on available configuration options, please refer to the [config.sample.yml](config.sample.yml) file.

### 3. Access the Web UI

Open your browser to [http://localhost:8000](http://localhost:8000)

---

## Local Installation (alternative to Docker installation)

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd mc-server-webadmin
```

### 2. Install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure

```bash
cp config.sample.yml config.yml
```

### 4. Run the server

```bash
python run.py --config config.yml
```

---
## Disclaimer

This software is provided as is, without any warranty. Use at your own risk. The author is not responsible for any damage caused by this software.

## License

See [LICENSE](LICENSE).
