import time
import httpx
import asyncio
from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.jose import jwt, JsonWebKey
from mcadmin.models.oidc_providers import OIDCProviders


class OIDCService:
    def __init__(self):
        self._cached_oidc_issuer_meta: dict = {}

    async def create_oidc_provider(self, **kwargs) -> OIDCProviders:
        oidc_provider = await OIDCProviders.create(**kwargs)

        await self._ensure_auto_launch_unique(oidc_provider)

        return oidc_provider

    async def get_oidc_provider(self, **kwargs) -> OIDCProviders | None:
        oidc_provider = await OIDCProviders.get_or_none(**kwargs)

        return oidc_provider

    async def list_oidc_providers(self) -> list[OIDCProviders]:
        return await OIDCProviders.all().order_by("id")

    async def update_oidc_provider(self, oidc_provider: OIDCProviders, **kwargs) -> None:
        oidc_provider.update_from_dict(kwargs)
        await oidc_provider.save()

        await self._ensure_auto_launch_unique(oidc_provider)

        self._cached_oidc_issuer_meta = {}

    async def delete_oidc_provider(self, oidc_provider: OIDCProviders) -> None:
        await oidc_provider.delete()

        self._cached_oidc_issuer_meta = {}

    async def valid_issuer_url(self, issuer_url: str) -> bool:
        check_keys = ["issuer", "authorization_endpoint", "token_endpoint", "jwks_uri"]

        try:
            oidc_meta = await self.get_oidc_provider_meta(issuer_url, force_discovery=True)
            return all(key in oidc_meta for key in check_keys)
        except Exception:
            return False

    async def get_oidc_provider_meta(self, issuer_url: str, *, force_discovery: bool = False) -> dict:
        if not issuer_url.endswith("/"):
            issuer_url += "/"

        if issuer_url in self._cached_oidc_issuer_meta and not force_discovery:
            return self._cached_oidc_issuer_meta[issuer_url]

        # retry discovery max 3 times
        for _ in range(3):
            try:
                meta = await self._discover_oidc_provider_meta(issuer_url)
                break
            except Exception:
                # sleep and retry
                await asyncio.sleep(1)
                continue
        else:
            raise ValueError("Failed to discover OIDC provider metadata")

        self._cached_oidc_issuer_meta[issuer_url] = meta
        return meta

    async def gen_oidc_authorization_url(self, provider_config: dict, *, redirect_uri: str, state: str, nonce: str) -> str:
        client = self._gen_oidc_client(provider_config)
        oidc_meta = await self.get_oidc_provider_meta(provider_config['issuer_url'])
        authorization_endpoint = oidc_meta['authorization_endpoint']

        authorization_url, _ = client.create_authorization_url(
            authorization_endpoint,
            redirect_uri=redirect_uri,
            state=state,
            nonce=nonce
        )

        return authorization_url

    async def fetch_oidc_token(self, provider_config: dict, *, redirect_uri: str, response: str) -> dict:
        client = self._gen_oidc_client(provider_config)
        oidc_meta = await self.get_oidc_provider_meta(provider_config["issuer_url"])
        token_endpoint = oidc_meta['token_endpoint']

        token = await client.fetch_token(
            token_endpoint,
            authorization_response=response,
            redirect_uri=redirect_uri
        )

        return token

    async def validate_oidc_id_token(self, provider_config: dict, token: str, *, nonce: str) -> dict:
        oidc_meta = await self.get_oidc_provider_meta(provider_config["issuer_url"])
        jwks_uri = oidc_meta['jwks_uri']
        jwks = await self._fetch_oidc_provider_jwks(jwks_uri)
        key_set = JsonWebKey.import_key_set(jwks)

        claims = jwt.decode(
            token,
            key_set,
            claims_options={
                "iss": {"values": [provider_config["issuer_url"]], "essential": True},
                "aud": {"values": [provider_config["client_id"]], "essential": True},
                "exp": {"essential": True},
                "iat": {"essential": True},
                "nonce": {"values": [nonce], "essential": True},
            },
        )
        claims.validate()
        return dict(claims)
    
    async def validate_oidc_logout_token(self, provider_config: dict, token: str) -> dict:
        oidc_meta = await self.get_oidc_provider_meta(provider_config["issuer_url"])
        jwks_uri = oidc_meta['jwks_uri']
        jwks = await self._fetch_oidc_provider_jwks(jwks_uri)
        key_set = JsonWebKey.import_key_set(jwks)

        claims = jwt.decode(
            token,
            key_set,
            claims_options={
                "iss": {"values": [provider_config["issuer_url"]], "essential": True},
                "aud": {"values": [provider_config["client_id"]], "essential": True},
                "exp": {"essential": True},
                "iat": {"essential": True},
            },
        )
        claims.validate()
        
        events = claims.get("events")
        if not isinstance(events, dict) or "http://schemas.openid.net/event/backchannel-logout" not in events:
            raise ValueError("Invalid logout token: missing backchannel logout event")

        if "nonce" in claims:
            raise ValueError("Invalid logout token: nonce must not be present")

        if not claims.get("sid") and not claims.get("sub"):
            raise ValueError("Invalid logout token: missing sid and sub")
        
        now = time.time()
        if claims["iat"] < now - 300:
            raise ValueError("Logout token too old")
        
        return dict(claims)

    async def get_oidc_provider_logout_endpoint(self, provider_config: dict) -> str:
        oidc_meta = await self.get_oidc_provider_meta(provider_config['issuer_url'])
        end_session_endpoint = oidc_meta['end_session_endpoint']

        return end_session_endpoint

    async def _ensure_auto_launch_unique(self, oidc_provider: OIDCProviders) -> None:
        if not oidc_provider.auto_launch:
            return
        
        await OIDCProviders.filter(auto_launch=True).exclude(id=oidc_provider.id).update(auto_launch=False)

    async def _fetch_oidc_provider_jwks(self, jwks_uri: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_uri)
            response.raise_for_status()
            return response.json()

    async def _discover_oidc_provider_meta(self, issuer_url: str) -> dict:
        well_known_url = issuer_url + ".well-known/openid-configuration"

        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(well_known_url)
            response.raise_for_status()
            return response.json()

    def _gen_oidc_client(self, provider_config: dict) -> AsyncOAuth2Client:
        return AsyncOAuth2Client(
            client_id=provider_config['client_id'],
            client_secret=provider_config['client_secret'],
            scope=provider_config['scope'],
            token_endpoint_auth_method="client_secret_post"
        )
