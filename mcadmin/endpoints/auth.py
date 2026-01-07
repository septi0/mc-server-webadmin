import logging
import aiohttp_jinja2
import secrets
from aiohttp import request, web
from aiohttp_session import get_session
from mcadmin.services.auth_config import AuthConfigService
from mcadmin.services.oidc import OIDCService
from mcadmin.utils.url import sanitize_url_path
from mcadmin.utils.web import get_di
from mcadmin.utils.validate import validate_data, require_roles
from mcadmin.services.users import UsersService
from mcadmin.schemas.users import AuthSchema, CreatePasswordlessUserSchema

auth_routes = web.RouteTableDef()
logger = logging.getLogger(__name__)


@auth_routes.get("/login")
@auth_routes.post("/login")
@require_roles(["guest"])
@aiohttp_jinja2.template("login.html")
async def login_template(request: web.Request):
    users_service: UsersService = get_di(request).users_service
    auth_config_service: AuthConfigService = get_di(request).auth_config_service
    oidc_service: OIDCService = get_di(request).oidc_service
    data = {}

    auth_methods = await auth_config_service.get_auth_methods()
    oidc_providers = await oidc_service.list_oidc_providers()

    local_login = auth_config_service.local_login_allowed(auth_methods, oidc_providers)
    oidc_login = auth_methods and "oidc" in auth_methods

    if oidc_login and oidc_providers:
        # search if any provider has auto_launch
        auto_launch_provider = next((p for p in oidc_providers if p.auto_launch), None)

        if auto_launch_provider:
            raise web.HTTPFound(f"/login/oidc/{auto_launch_provider.id}")

    data["local_login"] = local_login
    data["oidc_login"] = oidc_login
    data["oidc_providers"] = oidc_providers if oidc_login else None

    if request.method == "GET":
        return data

    if not local_login:
        data["message"] = ("danger", "Local login is disabled. Please authenticate using OIDC.")
        return data

    session = await get_session(request)
    post_data = await request.post()
    get_data = request.query

    username = str(post_data.get("username", ""))
    password = str(post_data.get("password", ""))
    next_url = sanitize_url_path(get_data.get("redirect", "/dashboard"))

    try:
        validate_data(AuthSchema, {"username": username, "password": password})
    except Exception as e:
        data["message"] = ("danger", str(e))
        return data

    user = await users_service.check_password(username, password)

    if user:
        session["user_id"] = user.id
        session["username"] = user.username
        session["role"] = user.role
        session["auth_method"] = "local"

        logger.info(f"New login for user '{username}' (ip: {request['real_ip']})")
        raise web.HTTPFound(next_url if next_url else "/dashboard")

    logger.warning(f"Failed login attempt for user '{username}' (ip: {request['real_ip']})")

    data["message"] = ("danger", "Invalid credentials")
    data["last_username"] = username

    return data


@auth_routes.get("/login/oidc/{provider_id}")
@require_roles(["guest"])
async def login_oidc_redirect(request: web.Request):
    auth_config_service: AuthConfigService = get_di(request).auth_config_service
    oidc_service: OIDCService = get_di(request).oidc_service

    provider_id = request.match_info.get("provider_id", 0)
    auth_methods = await auth_config_service.get_auth_methods()
    oidc_login = auth_methods and "oidc" in auth_methods

    if not oidc_login:
        raise web.HTTPFound("/login")

    provider = await oidc_service.get_oidc_provider(id=provider_id)

    if not provider:
        raise web.HTTPNotFound()

    session = await get_session(request)
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    redirect_uri = str(request.url.origin()) + f"/login/oidc/{provider_id}/callback"
    auth_url = await oidc_service.gen_oidc_authorization_url(provider.config, redirect_uri=redirect_uri, state=state, nonce=nonce)

    session["oidc_state"] = state
    session["oidc_nonce"] = nonce
    session["oidc_provider"] = provider.id

    logger.info(f"Redirecting user to OIDC provider '{provider.name}' authorization endpoint. Redirect uri: {redirect_uri}")

    raise web.HTTPFound(auth_url)


@auth_routes.get("/login/oidc/{provider_id}/callback")
@require_roles(["guest"])
async def login_oidc_callback(request: web.Request):
    oidc_service: OIDCService = get_di(request).oidc_service
    users_service: UsersService = get_di(request).users_service

    provider_id = request.match_info.get("provider_id", 0)
    provider = await oidc_service.get_oidc_provider(id=provider_id)
    get_data = request.query

    if not provider:
        raise web.HTTPNotFound()

    session = await get_session(request)

    expected_state = session.get("oidc_state")
    expected_nonce = session.get("oidc_nonce", "")
    expected_provider = session.get("oidc_provider")
    received_state = get_data.get("state")

    if expected_state:
        session.pop("oidc_state")

    if expected_nonce:
        session.pop("oidc_nonce")

    if expected_provider != provider.id:
        logger.warning(f"Invalid provider parameter: {expected_provider} != {provider.id}")
        return web.Response(text="Invalid provider parameter", status=400)

    if not received_state or not expected_state or received_state != expected_state:
        logger.warning(f"Invalid state parameter: {received_state} != {expected_state}")
        return web.Response(text="Invalid state parameter", status=400)

    redirect_uri = str(request.url.origin()) + f"/login/oidc/{provider_id}/callback"

    try:
        token = await oidc_service.fetch_oidc_token(provider.config, response=str(request.url), redirect_uri=redirect_uri)
    except Exception as e:
        logger.exception(f"Error fetching OIDC token: {e}")
        return web.Response(text=f"Error fetching OIDC token: {e}", status=400)

    try:
        data = await oidc_service.validate_oidc_id_token(provider.config, token=token, nonce=expected_nonce)
    except Exception as e:
        logger.exception(f"Error validating OIDC ID token: {e}")
        return web.Response(text=f"Error validating OIDC ID token", status=400)

    oidc_sub = data.get("sub", "")
    oidc_username = data.get("preferred_username", "")

    user = await users_service.get_user_by_identity(provider, oidc_sub)

    if not user:
        session["link_account_sub"] = oidc_sub
        session["link_account_username"] = oidc_username

        raise web.HTTPFound("/login/link_account")

    session["user_id"] = user.id
    session["username"] = user.username
    session["role"] = user.role
    session["auth_method"] = "oidc"

    logger.info(f"New login via {provider.name} for user '{user.username}' (ip: {request['real_ip']})")
    raise web.HTTPFound("/dashboard")

@auth_routes.get("/login/link_account")
@auth_routes.post("/login/link_account")
@require_roles(["guest"])
@aiohttp_jinja2.template("link_account.html")
async def link_account_template(request: web.Request):
    auth_config_service: AuthConfigService = get_di(request).auth_config_service
    oidc_service: OIDCService = get_di(request).oidc_service
    users_service: UsersService = get_di(request).users_service
    session = await get_session(request)
    data = {}

    provider_id = session.get("oidc_provider")
    suggested_username = session.get("link_account_username")

    data["suggested_username"] = suggested_username

    if not provider_id:
        raise web.HTTPNotFound()

    provider = await oidc_service.get_oidc_provider(id=provider_id)

    if not provider:
        raise web.HTTPNotFound()

    data["provider"] = provider

    auth_methods = await auth_config_service.get_auth_methods()
    oidc_providers = await oidc_service.list_oidc_providers()

    allow_registration = provider.allow_registration
    allow_link_account = auth_config_service.local_login_allowed(auth_methods, oidc_providers)

    data["allow_registration"] = allow_registration
    data["allow_link_account"] = allow_link_account
    data['active_tab'] = 'register' if allow_registration else 'link_account'

    if not allow_registration and not allow_link_account:
        data["message"] = ("danger", "Registration and linking accounts are both disabled by administrator.")
        return data

    if request.method == "GET":
        return data

    post_data = await request.post()
    action = str(post_data.get("action", ""))

    if action == "register":
        if not allow_registration:
            data["message"] = ("danger", "Registration is disabled. Please contact your administrator.")
            return data

        username = str(post_data.get("username", ""))
        role = "user"

        try:
            validate_data(CreatePasswordlessUserSchema, {"username": username, "role": role})
        except Exception as e:
            data["message"] = ("danger", str(e))
            return data

        if await users_service.get_user(username=username):
            data["message"] = ("danger", "User already exists. Please choose a different username or link your account.")
            return data

        try:
            user = await users_service.create_user(username=username, password="", role=role)
            await users_service.add_user_identity(user, provider, session.get("link_account_sub", ""))
        except Exception as e:
            logger.exception(f"Error creating user during OIDC registration: {e}")
            data["message"] = ("danger", "Error creating user. Please try again later.")
            return data
    elif action == "link_account":
        username = str(post_data.get("username", ""))
        password = str(post_data.get("password", ""))

        try:
            validate_data(AuthSchema, {"username": username, "password": password})
        except Exception as e:
            data["message"] = ("danger", str(e))
            return data

        user = await users_service.check_password(username, password)

        if not user:
            data["message"] = ("danger", "Invalid credentials")
            return data

        try:
            await users_service.add_user_identity(user, provider, session.get("link_account_sub", ""))
        except Exception as e:
            logger.exception(f"Error linking user account during OIDC login: {e}")
            data["message"] = ("danger", "Error linking user account. Please try again later.")
            return data
    else:
        data["message"] = ("danger", "Invalid action.")
        return data

    session["user_id"] = user.id
    session["username"] = user.username
    session["role"] = user.role
    session["auth_method"] = "oidc"

    logger.info(f"New user '{username}' registered via {provider.name} (ip: {request['real_ip']})")
    raise web.HTTPFound("/dashboard")


@auth_routes.get("/logout")
@require_roles(["user", "admin"])
async def logout(request: web.Request):
    oidc_service: OIDCService = get_di(request).oidc_service
    session = await get_session(request)
    redirect_location = "/login"

    if session.get("auth_method") == "oidc":
        # Handle OIDC logout
        provider = await oidc_service.get_oidc_provider(id=session.get("oidc_provider"))

        if provider:
            redirect_location = await oidc_service.get_oidc_provider_logout_endpoint(provider.config)

    session.invalidate()

    logger.info(f"User '{request['auth_username']}' logged out")

    raise web.HTTPFound(redirect_location)
