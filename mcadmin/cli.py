import logging
from mcadmin.libraries.di_container import DiContainer
from mcadmin.services.users import UsersService
from mcadmin.schemas.users import CreateUserSchema, UpdateUserSchema
from mcadmin.utils.validate import validate_data

__all__ = ["McServerWebadminCli"]
logger = logging.getLogger(__name__)


class McServerWebadminCli:
    def __init__(self, category: str, *, di: DiContainer) -> None:
        self._handlers = {
            "dev": McServerWebadminDevCli,
            "users": McServerWebadminUsersCli,
        }

        handler = self._handlers.get(category)

        if not handler:
            raise ValueError(f"Unknown command: {category}")

        self._handler = handler(di=di)

    async def run(self, command: str, **kwargs) -> None:
        await self._handler.run(command, **kwargs)


class McServerWebadminDevCli:
    def __init__(self, *, di: DiContainer) -> None:
        self._di = di
        self._handlers = {
            "generate-migrations": self.generate_migrations,
        }

    async def run(self, command: str, **kwargs) -> None:
        handler = self._handlers.get(command)

        if not handler:
            raise ValueError(f"Unknown command: {command}")

        await handler(**kwargs)

    async def generate_migrations(self, *, aerich_cmd) -> None:
        logger.info("Generating database migrations...")
        
        await aerich_cmd.migrate()

        logger.info("Database migrations generated successfully")


class McServerWebadminUsersCli:
    def __init__(self, *, di: DiContainer) -> None:
        self._di = di
        self._handlers = {
            "list": self.list_users,
            "create": self.create_user,
            "update": self.update_user,
            "delete": self.delete_user,
        }

    async def run(self, command: str, **kwargs) -> None:
        handler = self._handlers.get(command)

        if not handler:
            raise ValueError(f"Unknown command: {command}")

        await handler(**kwargs)

    async def list_users(self) -> None:
        users_service: UsersService = self._di.users_service

        users = await users_service.list_users()
        users_str = ""
        
        for user in users:
           users_str += f"User: {user.username}, Role: {user.role}\n"

        logger.info(f"Users:\n\n{users_str}")

    async def create_user(self, *, username: str, role: str, password: str) -> None:
        users_service: UsersService = self._di.users_service

        try:
            validate_data(CreateUserSchema, {"username": username, "role": role, "password": password})
        except Exception as e:
            logger.error(f"Invalid data: {e}")
            return

        if await users_service.get_user(username=username):
            logger.error(f"User already exists: {username}")
            return

        logger.info(f"Creating user: {username}")

        try:
            await users_service.create_user(username=username, role=role, password=password)
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return

        logger.info(f"User created successfully: {username}")

    async def update_user(self, *, username: str, role: str = "", password: str = "") -> None:
        users_service: UsersService = self._di.users_service

        if not role and not password:
            logger.error(f"Nothing to update for user: {username}")
            return

        user = await users_service.get_user(username=username)

        if not user:
            logger.error(f"User not found: {username}")
            return

        data = {}

        if password:
            data["password"] = password

        data["role"] = role if role else user.role

        try:
            validate_data(UpdateUserSchema, data)
        except Exception as e:
            logger.error(f"Invalid data: {e}")
            return

        logger.info(f"Updating user: {username}")

        try:
            await users_service.update_user(user, **data)
        except Exception as e:
            logger.error(f"Failed to update user: {e}")
            return

        logger.info(f"User updated successfully: {username}")

    async def delete_user(self, *, username: str) -> None:
        users_service: UsersService = self._di.users_service

        user = await users_service.get_user(username=username)

        if not user:
            logger.error(f"User not found: {username}")
            return

        logger.info(f"Deleting user: {username}")

        try:
            await users_service.delete_user(user)
        except Exception as e:
            logger.error(f"Failed to delete user: {e}")
            return

        logger.info(f"User deleted successfully: {username}")
