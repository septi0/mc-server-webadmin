import logging
import os
import aiofiles


__all__ = [
    "McServerPropertyError",
    "McServerPropertiesGenerator",
]

logger = logging.getLogger(__name__)


class McServerPropertyError(Exception):
    pass


class McServerPropertiesGenerator:
    """Low level server.properties generator and validator"""

    properties: dict = {
        "level-seed": {"empty": True},
        "gamemode": {"values": ["survival", "creative", "adventure", "spectator"]},
        "enable-command-block": {"type": "bool"},
        "motd": {"empty": True},
        "pvp": {"type": "bool"},
        "generate-structures": {"type": "bool"},
        "difficulty": {"values": ["peaceful", "easy", "normal", "hard"]},
        "max-players": {"type": "int"},
        "allow-flight": {"type": "bool"},
        "view-distance": {"type": "int"},
        "allow-nether": {"type": "bool"},
        "hide-online-players": {"type": "bool"},
        "simulation-distance": {"type": "int"},
        "force-gamemode": {"type": "bool"},
        "hardcore": {"type": "bool"},
        "white-list": {"type": "bool"},
        "spawn-npcs": {"type": "bool"},
        "spawn-animals": {"type": "bool"},
        "level-type": {"values": ["default", "flat", "large_biomes", "amplified"]},
        "spawn-monsters": {"type": "bool"},
        "enforce-whitelist": {"type": "bool"},
        "rcon.password": {"empty": True},
    }

    level_types: list[str] = ["default", "flat", "large_biomes", "amplified"]

    min_server_version: str = "1.7.10"

    def __init__(self, instance_dir: str, *, server_ip: str, server_port: int, rcon_port: int) -> None:
        self._instance_dir: str = instance_dir
        self._enforced_properties: dict = {
            "server-port": str(server_port),
            "rcon.port": str(rcon_port),
            "server-ip": server_ip,
        }

    async def generate(self, properties: dict) -> None:
        logger.info(f"Generating server.properties")

        self.validate_properties(properties)

        properties_file = os.path.join(self._instance_dir, "server.properties")

        if properties.get("rcon.password"):
            self._enforced_properties["enable-rcon"] = "true"

        async with aiofiles.open(properties_file, "w") as f:
            for key, value in self._enforced_properties.items():
                await f.write(f"{key}={value}\n")

            for key, value in properties.items():
                await f.write(f"{key}={value}\n")

        logger.info(f"server.properties generated successfully")

    @classmethod
    def validate_properties(cls, properties: dict) -> None:
        for key, value in properties.items():
            if key not in cls.properties:
                raise McServerPropertyError(f"Unknown property: {key}")

            prop_info = cls.properties[key]

            prop_empty = prop_info.get("empty", False)
            prop_values = prop_info.get("values", [])
            prop_type = prop_info.get("type", "str")

            if not prop_empty and value == "":
                raise McServerPropertyError(f"Property '{key}' cannot be empty")

            if prop_values and value not in prop_values:
                raise McServerPropertyError(f"Property '{key}' must be one of {prop_values}")

            if prop_type == "int" and not value.isdigit():
                raise McServerPropertyError(f"Property '{key}' must be an integer")

            if prop_type == "bool" and value not in ["true", "false"]:
                raise McServerPropertyError(f"Property '{key}' must be a boolean")
