#!/usr/bin/env python3
"""
An MCP (Model Context Protocol) server over stdio that wraps the agentic
application's own HTTP surface -- the thing that makes it "fully agentic native"
rather than something an agent can only reach by shelling out to curl.

This process is a thin, stateless translator, not a second source of truth:
it asks the running app's own `GET /` for the current action registry on
every `tools/list` call, and turns each `Action` into an MCP tool whose
`inputSchema` is built from that same `Action`'s `params`. Add a capability
to the app's own registry and it appears here automatically,
with no change to this file -- the alternative, a second hand-maintained
tool list here, is exactly the kind of drift we avoid for its call sites,
and duplicating that mistake across a language boundary would be worse, not
better.

No dependencies beyond the standard library on purpose: this is a prototype,
and `pip install mcp` is one more thing to go wrong before it can be tried.

Protocol: JSON-RPC 2.0, one message per line, over stdin/stdout -- MCP's own
stdio transport. Diagnostics go to stderr, never stdout, because stdout is
the wire.

Usage (registered in `.mcp.json`):
    AGENTIC_HTTP_PORT=7330 python3 scripts/agentic_mcp_server.py

The port must match whatever HTTP port the app itself was
launched with -- this script only speaks to that port, never picks one.
"""

import json
import os
import sys
import urllib.error
import urllib.request

PORT = os.environ.get("AGENTIC_HTTP_PORT", "7330")
APP_URL = f"http://127.0.0.1:{PORT}"
PROTOCOL_VERSION = "2024-11-05"


def log(message):
    print(f"[agentic_mcp_server] {message}", file=sys.stderr, flush=True)


def app_request(method, path, timeout=15):
    """One HTTP call to the app's own HTTP surface. Raises on any
    failure -- the caller decides how that becomes an MCP error, this
    function's job is only to talk to the socket."""
    req = urllib.request.Request(APP_URL + path, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def json_schema_type(kind):
    # `Param::kind` is a free-form string today
    # ("string"/"integer"), not an enum -- this is the one place that
    # vocabulary has to agree with JSON Schema's own, so an unrecognised
    # kind falls back to "string" rather than producing an invalid schema.
    return kind if kind in ("string", "integer", "boolean", "number") else "string"


def action_to_tool(action):
    properties = {}
    required = []
    for param in action["params"]:
        properties[param["name"]] = {
            "type": json_schema_type(param["kind"]),
            "description": param["description"],
        }
        required.append(param["name"])
    return {
        "name": action["name"],
        "description": f"{action['description']} ({action['method']} {action['path']})",
        "inputSchema": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
    }


def build_path(action, arguments):
    path = action["path"]
    for param in action["params"]:
        placeholder = "{" + param["name"] + "}"
        if param["name"] not in arguments:
            raise ValueError(f"missing required argument: {param['name']}")
        path = path.replace(placeholder, str(arguments[param["name"]]))
    return path


def handle_initialize(params):
    return {
        "protocolVersion": params.get("protocolVersion", PROTOCOL_VERSION),
        "capabilities": {"tools": {}},
        "serverInfo": {"name": "agentic-app", "version": "0.1.0"},
    }


def handle_tools_list():
    try:
        capabilities = app_request("GET", "/")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        # No tools rather than an error: a client that lists tools before
        # the app is even up should see "nothing yet", not a broken
        # connection it has no way to act on.
        log(f"could not reach {APP_URL}/ -- is the app running with "
            f"AGENTIC_HTTP_PORT={PORT}? ({e})")
        return {"tools": []}
    return {"tools": [action_to_tool(a) for a in capabilities["actions"]]}


def handle_tools_call(params):
    name = params.get("name")
    arguments = params.get("arguments") or {}
    try:
        capabilities = app_request("GET", "/")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return error_result(f"could not reach the app at {APP_URL}: {e}")

    action = next((a for a in capabilities["actions"] if a["name"] == name), None)
    if action is None:
        return error_result(f"no such action: {name}")

    try:
        path = build_path(action, arguments)
    except ValueError as e:
        return error_result(str(e))

    try:
        result = app_request(action["method"], path)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return error_result(f"{action['method']} {path} failed: {e}")

    return {"content": [{"type": "text", "text": json.dumps(result)}], "isError": False}


def error_result(message):
    return {"content": [{"type": "text", "text": message}], "isError": True}


def handle(request):
    method = request.get("method")
    params = request.get("params") or {}
    if method == "initialize":
        return handle_initialize(params)
    if method == "tools/list":
        return handle_tools_list()
    if method == "tools/call":
        return handle_tools_call(params)
    if method == "ping":
        return {}
    raise KeyError(method)


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as e:
            log(f"bad JSON-RPC line, dropped: {e}")
            continue

        # A notification (no `id`) gets no response, by the JSON-RPC spec
        # this transport follows -- `notifications/initialized` is the one
        # every client sends, and this app has no state to update on it.
        request_id = request.get("id")
        if request_id is None:
            log(f"notification: {request.get('method')}")
            continue

        try:
            result = handle(request)
            response = {"jsonrpc": "2.0", "id": request_id, "result": result}
        except KeyError as e:
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"method not found: {e}"},
            }
        except Exception as e:  # noqa: BLE001 -- a bad request must not kill the server
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32603, "message": str(e)},
            }

        print(json.dumps(response), flush=True)


if __name__ == "__main__":
    log(f"starting, will talk to {APP_URL}")
    main()
