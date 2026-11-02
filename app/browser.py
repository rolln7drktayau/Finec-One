"""ASGI bridge for the isolated browser worker; reuse real validation and rules."""
import inspect
import json
from functools import wraps
from urllib.parse import urlsplit
from .main import app
from .seed import seed


def asynchronous(call):
    @wraps(call)
    async def wrapped(*args, **kwargs):
        return call(*args, **kwargs)
    return wrapped


def prepare(dependant):
    # A browser worker has no Python thread pool. Run synchronous handlers on
    # its own event loop; requests are serialized by the JavaScript worker.
    if dependant.call and not inspect.iscoroutinefunction(dependant.call):
        dependant.call = asynchronous(dependant.call)
        # FastAPI versions may cache this property.
        dependant.__dict__.pop("is_coroutine_callable", None)
    for dependency in dependant.dependencies:
        prepare(dependency)


for route in app.routes:
    if hasattr(route, "dependant"):
        prepare(route.dependant)
        # Rebuild the handler after changing the endpoint's coroutine status.
        from starlette.routing import request_response
        route.app = request_response(route.get_route_handler())

seed()


async def browser_request(raw):
    request = json.loads(raw)
    url = urlsplit(request["path"])
    body = (request.get("body") or "").encode()
    messages = []

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message):
        messages.append(message)

    scope = {"type": "http", "asgi": {"version": "3.0"},
             "http_version": "1.1", "method": request["method"],
             "scheme": "https", "path": url.path, "raw_path": url.path.encode(),
             "query_string": url.query.encode(), "root_path": "",
             "headers": [(k.lower().encode(), v.encode()) for k, v in request.get("headers", {}).items()],
             "client": ("browser", 0), "server": ("browser", 443)}
    await app(scope, receive, send)
    start = next(m for m in messages if m["type"] == "http.response.start")
    return json.dumps({"status": start["status"],
                       "headers": {k.decode(): v.decode() for k, v in start["headers"]},
                       "body": b"".join(m.get("body", b"") for m in messages).decode()})
