from mcadmin.models.app_config import AppConfig


class AuthConfigService:
    def __init__(self):
        pass

    async def get_auth_methods(self) -> list:
        auth_methods = await AppConfig.get_or_none(key="auth_methods")

        if not auth_methods:
            return []

        return auth_methods.value.split(",") if auth_methods else []

    async def update_auth_methods(self, methods: list) -> None:
        await AppConfig.update_or_create(key="auth_methods", defaults={"value": ",".join(methods)})

    def local_login_allowed(self, auth_methods: list, oidc_providers: list) -> bool:
        return not auth_methods or "local" in auth_methods or not oidc_providers