import bcrypt
from mcadmin.models.users import Users


class UsersService:
    def __init__(self):
        pass

    async def create_user(self, **kwargs) -> Users:
        kwargs["password"] = self._hash_password(kwargs["password"])

        user = await Users.create(**kwargs)
        return user

    async def get_user(self, **kwargs) -> Users | None:
        user = await Users.get_or_none(**kwargs)

        return user

    async def update_user(self, user: Users, **kwargs) -> None:
        if "password" in kwargs:
            kwargs["password"] = self._hash_password(kwargs["password"])

        user.update_from_dict(kwargs)
        await user.save()

    async def delete_user(self, user: Users) -> None:
        await user.delete()

    async def list_users(self) -> list[Users]:
        return await Users.all().order_by("id")

    async def check_password(self, username: str, password: str) -> Users | None:
        user = await Users.get_or_none(username=username)

        if not user:
            return None

        return user if bcrypt.checkpw(password.encode(), user.password.encode()) else None

    def _hash_password(self, password: str) -> str:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode(), salt)

        return hashed.decode()
