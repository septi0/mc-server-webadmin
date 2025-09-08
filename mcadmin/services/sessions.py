from mcadmin.models.sessions import Sessions


class SessionsService:
    def __init__(self):
        pass

    async def get_user_sessions(self, user_id: int) -> list[Sessions] | None:
        sessions = await Sessions.filter(user_id=user_id).order_by("-created_at")

        return sessions

    async def delete_user_session(self, user_id: int, session_id: int) -> None:
        await Sessions.filter(user_id=user_id, id=session_id).delete()
