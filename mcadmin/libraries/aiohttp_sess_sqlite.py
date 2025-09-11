import uuid
import random
from datetime import datetime, timedelta, timezone
from aiohttp_session import AbstractStorage, Session
from aiohttp import web
from tortoise.models import Model as TortoiseModel
from typing import Type
from user_agents import parse as parse_ua

__all__ = ["SqliteTortoiseStorage"]


class SqliteTortoiseStorage(AbstractStorage):

    def __init__(
        self,
        session: Type[TortoiseModel],
        *,
        match_ip: bool = False,
        match_user_agent: bool = True,
        **kwargs,
    ) -> None:
        self._sess_model: Type[TortoiseModel] = session
        self.match_ip = match_ip
        self.match_user_agent = match_user_agent

        super().__init__(**kwargs)

    async def load_session(self, request: web.Request) -> Session:
        await self._sess_gc()

        cookie = request.cookies.get(self.cookie_name)

        if cookie is None:
            return Session(None, data=None, new=True, max_age=self.max_age)

        token = str(cookie)

        row = await self._sess_model.get_or_none(token=token)

        if not row:
            return Session(None, data=None, new=True, max_age=self.max_age)

        if row.expiry and row.expiry < datetime.now(timezone.utc):  # type: ignore
            await row.delete()
            return Session(None, data=None, new=True, max_age=self.max_age)

        # match ip
        if self.match_ip and row.ip != self._get_ip(request):  # type: ignore
            await row.delete()
            return Session(None, data=None, new=True, max_age=self.max_age)

        # match user agent
        if self.match_user_agent and row.user_agent != request.headers.get("User-Agent", "unknown"):  # type: ignore
            await row.delete()
            return Session(None, data=None, new=True, max_age=self.max_age)

        data = self._decoder(row.data)  # type: ignore

        return Session(token, data=data, new=False, max_age=self.max_age)  # type: ignore

    async def save_session(self, request: web.Request, response: web.StreamResponse, session: Session) -> None:
        token = session.identity
        data = self._get_session_data(session)
        data_str = self._encoder(data)
        sess_data = data.get("session", {})

        if token is None:
            token = uuid.uuid4().hex
            expiry = None

            if session.max_age is not None:
                expiry = datetime.now(timezone.utc) + timedelta(seconds=session.max_age)

            self.save_cookie(response, token, max_age=session.max_age)

            await self._sess_model.create(
                token=token,
                user_id=sess_data.get("user_id"),
                ip=self._get_ip(request),
                user_agent=request.headers.get("User-Agent", ""),
                device=self._ua_to_device(request.headers.get("User-Agent", "")),
                data=data_str,
                expiry=expiry,
            )
        else:
            token = str(token)

            if session.empty:
                self.save_cookie(response, "", max_age=session.max_age)
                await self._sess_model.filter(token=token).delete()
            else:
                await self._sess_model.filter(token=token).update(data=data_str, updated_at=datetime.now(timezone.utc))

    async def _sess_gc(self) -> None:
        if random.randint(1, 100) == 1:
            await self._sess_model.filter(expiry__lt=datetime.now(timezone.utc)).delete()

    def _ua_to_device(self, user_agent: str) -> str:
        if not user_agent:
            return "Unknown device"

        ua = parse_ua(user_agent)
        browser = ua.browser.family or "Unknown"
        os = ua.os.family or "Unknown"
        device_type = "PC" if ua.is_pc else ("Mobile" if ua.is_mobile else "Tablet" if ua.is_tablet else "Bot" if ua.is_bot else "Other")

        return f"{browser} on {os} ({device_type})"

    def _get_ip(self, request: web.Request) -> str:
        return request.get("real_ip", request.remote) or ""