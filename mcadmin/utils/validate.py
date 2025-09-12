from typing import Callable, Type
from pydantic import BaseModel, ValidationError
from aiohttp import web

__all__ = ["require_roles", "validate_request_schema"]


def require_roles(roles: list[str]) -> Callable:
    def decorator(handler):
        handler.required_roles = roles
        return handler

    return decorator

def validate_request_schema(schema: Type[BaseModel]) -> Callable:
    def decorator(handler):
        async def wrapper(request):
            try:
                data = await request.post()
                obj = schema.model_validate(data)
            except (ValidationError, ValueError) as e:
                if isinstance(e, ValidationError):
                    errors = []

                    for err in e.errors():
                        field_id = str(err["loc"][0]) if err["loc"] else None

                        if field_id:
                            field = schema.model_fields.get(field_id, None)
                            title = field.title or field_id if field else field_id

                            errors.append(f"{title}: {err['msg']}")
                        else:
                            errors.append(err["msg"])
                else:
                    errors = [str(e)]
                return web.json_response({"status": "error", "message": ", ".join(errors)}, status=403)

            return await handler(request)

        return wrapper

    return decorator