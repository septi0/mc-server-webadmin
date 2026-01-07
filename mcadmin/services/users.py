import bcrypt
from mcadmin.models.users import Users
from mcadmin.models.user_identities import UserIdentities
from mcadmin.models.oidc_providers import OIDCProviders


class UsersService:
    def __init__(self):
        pass

    async def create_user(self, **kwargs) -> Users:
        if kwargs["password"]:
            kwargs["password"] = self._hash_password(kwargs["password"])

        user = await Users.create(**kwargs)
        return user

    async def add_user_identity(self, user: Users, provider: OIDCProviders, sub: str) -> UserIdentities:
        identity = await UserIdentities.create(user_id=user.id, provider_id=provider.id, sub=sub)

        return identity

    async def get_user(self, **kwargs) -> Users | None:
        user = await Users.get_or_none(**kwargs)

        return user

    async def get_user_by_identity(self, provider: OIDCProviders, sub: str) -> Users | None:
        identity = await UserIdentities.get_or_none(provider_id=provider.id, sub=sub)

        if not identity:
            return None

        user = await Users.get_or_none(id=identity.user_id)
        return user

    async def get_user_identities(self, user_id: int) -> list[UserIdentities]:
        identities = await UserIdentities.filter(user_id=user_id).order_by("-added_at")

        return identities

    async def get_user_identity(self, **kwargs) -> UserIdentities | None:
        identity = await UserIdentities.filter(**kwargs).first()

        return identity

    async def update_user(self, user: Users, **kwargs) -> None:
        if "password" in kwargs and kwargs["password"]:
            kwargs["password"] = self._hash_password(kwargs["password"])

        user.update_from_dict(kwargs)
        await user.save()

    async def delete_user(self, user: Users) -> None:
        await user.delete()
        await UserIdentities.filter(user_id=user.id).delete()

    async def delete_user_identity(self, user_identity: UserIdentities) -> None:
        await user_identity.delete()

    async def list_users(self) -> list[Users]:
        return await Users.all().order_by("id")

    async def check_password(self, username: str, password: str, *, validate_passwordless: bool = False) -> Users | None:
        user = await Users.get_or_none(username=username)

        if not user:
            return None
        
        if not user.password:
            return user if validate_passwordless else None

        return user if bcrypt.checkpw(password.encode(), user.password.encode()) else None

    def _hash_password(self, password: str) -> str:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode(), salt)

        return hashed.decode()
