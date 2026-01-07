import json
import logging
import aiohttp_jinja2
from aiohttp import web
from mcadmin.utils.web import get_di
from mcadmin.utils.validate import require_roles, validate_request
from mcadmin.utils.convert import str_to_bool
from mcadmin.services.auth_config import AuthConfigService
from mcadmin.services.oidc import OIDCService
from mcadmin.services.users import UsersService
from mcadmin.schemas.auth_methods import UpdateAuthMethodsSchema
from mcadmin.schemas.oidc_providers import CreateOIDCProviderSchema, UpdateOIDCProviderSchema

admin_auth_config_routes = web.RouteTableDef()
logger = logging.getLogger(__name__)


@admin_auth_config_routes.get("/admin/authentication")
@require_roles(["admin"])
@aiohttp_jinja2.template("authentication.html")
async def authentication_template(request: web.Request):
    base_url: str = get_di(request).base_url
    data = {}

    data["uri_base"] = f"{request['proto']}://{request.host}{base_url}"

    return data


@admin_auth_config_routes.get("/api/admin/auth_config/methods")
@require_roles(["admin"])
async def admin_auth_methods_get(request: web.Request):
    auth_config_service: AuthConfigService = get_di(request).auth_config_service

    auth_methods = await auth_config_service.get_auth_methods()
    return web.json_response(auth_methods)


@admin_auth_config_routes.post("/api/admin/auth_config/methods")
@require_roles(["admin"])
@validate_request(UpdateAuthMethodsSchema)
async def admin_auth_methods_post(request: web.Request):
    auth_config_service: AuthConfigService = get_di(request).auth_config_service
    users_service: UsersService = get_di(request).users_service

    post_data = await request.post()

    auth_methods = json.loads(str(post_data.get("auth_methods", "[]")))
    
    if not "oidc" in auth_methods and await users_service.get_user_identity():
        return web.json_response({"status": "error", "message": "Cannot disable OIDC authentication while user identities are linked"}, status=400)

    try:
        await auth_config_service.update_auth_methods(auth_methods)
    except Exception as e:
        logger.exception(f"Failed to update authentication methods ({e})")
        return web.json_response({"status": "error", "message": f"Failed to update authentication methods ({e})"}, status=500)

    logger.info(f"Authentication methods updated: {auth_methods}")
    return web.json_response({"status": "success", "message": "Authentication methods updated successfully"})


@admin_auth_config_routes.get("/api/admin/auth_config/oidc-providers")
@require_roles(["admin"])
async def admin_oidc_providers_get(request: web.Request):
    oidc_service: OIDCService = get_di(request).oidc_service

    oidc_providers = await oidc_service.list_oidc_providers()

    if not oidc_providers:
        return web.json_response([])

    oidc_providers_list = []

    for s in oidc_providers:
        oidc_providers_list.append(
            {
                "id": s.id,
                "name": s.name,
                "default": s.default,
                "allow_registration": s.allow_registration,
                "auto_launch": s.auto_launch,
                "user_claim": s.user_claim,
                "created_at": str(s.created_at),
                "config": s.config,
            }
        )

    return web.json_response(oidc_providers_list)


@admin_auth_config_routes.post("/api/admin/auth_config/oidc-providers")
@require_roles(["admin"])
@validate_request(CreateOIDCProviderSchema)
async def admin_oidc_providers_post(request: web.Request):
    oidc_service: OIDCService = get_di(request).oidc_service

    post_data = await request.post()

    name = post_data.get("name")
    default = post_data.get("default", False)
    allow_registration = post_data.get("allow_registration", False)
    auto_launch = post_data.get("auto_launch", False)
    user_claim = post_data.get("user_claim", "")
    config = json.loads(str(post_data.get("config", "{}")))

    if not await oidc_service.valid_issuer_url(config["issuer_url"]):
        return web.json_response({"status": "error", "message": "Invalid issuer URL"}, status=400)

    try:
        await oidc_service.create_oidc_provider(
            name=name,
            default=default,
            allow_registration=allow_registration,
            auto_launch=auto_launch,
            user_claim=user_claim,
            config=config
        )
    except Exception as e:
        logger.exception(f"Failed to create OIDC provider ({e})")
        return web.json_response({"status": "error", "message": f"Failed to create OIDC provider ({e})"}, status=500)

    logger.info(f"OIDC provider created: {name}")
    return web.json_response({"status": "success", "message": "OIDC provider created successfully"})

@admin_auth_config_routes.post("/api/admin/auth_config/oidc-providers/{provider_id}")
@require_roles(["admin"])
@validate_request(UpdateOIDCProviderSchema)
async def admin_oidc_providers_update(request: web.Request):
    oidc_service: OIDCService = get_di(request).oidc_service

    provider_id = int(request.match_info.get("provider_id", 0))
    post_data = await request.post()

    name = post_data.get("name")
    default = str_to_bool(str(post_data.get("default", "false")))
    allow_registration = str_to_bool(str(post_data.get("allow_registration", "false")))
    auto_launch = str_to_bool(str(post_data.get("auto_launch", "false")))
    user_claim = post_data.get("user_claim", "")
    config = json.loads(str(post_data.get("config", "{}")))

    provider = await oidc_service.get_oidc_provider(id=provider_id)

    if not provider:
        return web.json_response({"status": "error", "message": "Provider not found"}, status=404)

    if not await oidc_service.valid_issuer_url(config["issuer_url"]):
        return web.json_response({"status": "error", "message": "Invalid issuer URL"}, status=400)

    try:
        await oidc_service.update_oidc_provider(
            provider,
            name=name,
            default=default,
            allow_registration=allow_registration,
            auto_launch=auto_launch,
            user_claim=user_claim,
            config=config
        )
    except Exception as e:
        logger.exception(f"Failed to update OIDC provider ({e})")
        return web.json_response({"status": "error", "message": f"Failed to update OIDC provider ({e})"}, status=500)

    logger.info(f"OIDC provider updated: {name}")
    return web.json_response({"status": "success", "message": "OIDC provider updated successfully"})

@admin_auth_config_routes.delete("/api/admin/auth_config/oidc-providers/{provider_id}")
@require_roles(["admin"])
async def admin_oidc_providers_delete(request: web.Request):
    oidc_service: OIDCService = get_di(request).oidc_service
    users_service: UsersService = get_di(request).users_service

    provider_id = int(request.match_info.get("provider_id", 0))

    provider = await oidc_service.get_oidc_provider(id=provider_id)

    if not provider:
        return web.json_response({"status": "error", "message": "Provider not found"}, status=404)
    
    if await users_service.get_user_identity(provider_id=provider.id):
        return web.json_response({"status": "error", "message": "Cannot delete provider with linked user identities"}, status=400)

    try:
        await oidc_service.delete_oidc_provider(provider)
    except Exception as e:
        logger.exception(f"Failed to delete OIDC provider ({e})")
        return web.json_response({"status": "error", "message": f"Failed to delete OIDC provider ({e})"}, status=500)

    logger.info(f"OIDC provider deleted: {provider.name}")
    return web.json_response({"status": "success", "message": "OIDC provider deleted successfully"})
