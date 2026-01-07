import sys
import os
import argparse
from pydantic import ValidationError
from mcadmin.manager import McServerWebadminManager
from mcadmin.exceptions import McServerWebadminRuntimeError
from mcadmin.info import __app_name__, __description__, __author__, __author_email__, __author_url__, __license__

__version__ = ""
with open(os.path.join(os.path.dirname(__file__), "VERSION"), "r") as f:
    __version__ = f.read().strip()


def main():
    # get args from command line
    parser = argparse.ArgumentParser(description=__description__)

    parser.add_argument("--config", dest="config_file", help="Path to the config file")
    parser.add_argument("--data", dest="data_directory", help="Path to the data directory")
    parser.add_argument("--log", dest="log_file", help="Log file where to write logs")
    parser.add_argument("--log-level", dest="log_level", help="Log level", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    parser.add_argument("--version", action="version", version=f"{__app_name__} {__version__}")

    subparsers = parser.add_subparsers(title="Commands", dest="command")

    dev_parser = subparsers.add_parser("dev", help="Dev commands")
    dev_subparsers = dev_parser.add_subparsers(title="Dev Commands", dest="subcommand", required=True)

    dev_gen_migrations = dev_subparsers.add_parser("generate-migrations", help="Generate database migrations")

    users_parser = subparsers.add_parser("users", help="User management commands")
    users_subparsers = users_parser.add_subparsers(title="User Commands", dest="subcommand", required=True)

    users_list_parser = users_subparsers.add_parser("list", help="List users")

    user_create_parser = users_subparsers.add_parser("create", help="Create a new user")
    user_create_parser.add_argument("--username", required=True, help="Username of the new user")
    user_create_parser.add_argument("--role", required=True, help="Role of the new user")
    user_create_parser.add_argument("--password", required=True, help="Password of the new user")

    user_update_parser = users_subparsers.add_parser("update", help="Update an existing user")
    user_update_parser.add_argument("--username", required=True, help="Username of the user to update")
    user_update_parser.add_argument("--role", required=True, help="New role of the user")
    user_update_parser.add_argument("--password", required=True, help="New password of the user")

    user_delete_parser = users_subparsers.add_parser("delete", help="Delete a user")
    user_delete_parser.add_argument("--username", required=True, help="Username of the user to delete")

    global_keys = ["log_file", "log_level", "config_file", "data_directory"]

    args = parser.parse_args()

    global_args = {key: getattr(args, key) for key in global_keys}
    cmd_args = {k: v for k, v in vars(args).items() if k not in global_keys}

    try:
        mcadmin = McServerWebadminManager(**global_args)
    except ValidationError as e:
        print(f"Configuration file contains {e.error_count()} error(s):")

        for error in e.errors(include_url=False):
            loc = ".".join(str(x) for x in error["loc"]) if error["loc"] else "general"
            print(f"  - {loc}: {error['msg']}")
            exit()

        print(f"\nCheck documentation for more information on how to configure Mc-Server-Webadmin")
        sys.exit(2)

    mcadmin.run(**cmd_args)

    sys.exit(0)
