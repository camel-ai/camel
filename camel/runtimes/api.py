# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
import asyncio
import concurrent.futures
import hmac
import importlib
import io
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from camel.toolkits import BaseToolkit

# thread pool for running sync tools that can't run inside async event loop
# (e.g., Playwright sync API)
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

logger = logging.getLogger(__name__)

# set environment variable to indicate we're running inside a CAMEL runtime
os.environ["CAMEL_RUNTIME"] = "true"

sys.path.append(os.getcwd())

modules_functions = sys.argv[1:]

logger.info(f"Modules and functions: {modules_functions}")

# API keys clients must present, read from ``CAMEL_RUNTIME_API_KEY`` as a
# comma-separated list.
#
# ``sys.argv`` is consumed in full as toolkit specifications above, so there is
# no CLI surface left to configure this through, and an environment variable is
# how the key reaches this process when a runtime starts it in a container.
#
# Refuse to start when the variable is absent, rather than inventing a key: a
# generated key would have to be written somewhere for the operator to use it,
# and a credential in a log file is its own problem. The runtimes in this
# package always set the variable, so this only affects starting the server by
# hand. Setting it to an empty value disables authentication explicitly, for a
# single-user trusted network.
_raw_api_key = os.environ.get("CAMEL_RUNTIME_API_KEY")

if _raw_api_key is None:
    raise RuntimeError(
        "CAMEL_RUNTIME_API_KEY is not set. This server publishes every "
        "registered tool as an HTTP endpoint, so it will not start without "
        "one. Set it to the key clients must present, as a comma-separated "
        "list for more than one, or to an empty value to serve without "
        "authentication on a trusted network."
    )

_API_KEYS: List[str] = [
    key.strip() for key in _raw_api_key.split(",") if key.strip()
]

if not _API_KEYS:
    logger.warning(
        "CAMEL_RUNTIME_API_KEY is empty: authentication is disabled and "
        "every registered tool is reachable by any client that can reach "
        "this port."
    )


def _keys_equal(left: str, right: str) -> bool:
    r"""Compare two keys without leaking their contents through timing.

    Both operands are encoded to UTF-8 first: ``hmac.compare_digest`` accepts
    ``str`` only while it stays inside ASCII, and a header value can hold more
    than that. Anything that will not encode is reported as a mismatch instead
    of raising.

    Args:
        left (str): One key value.
        right (str): The other key value.

    Returns:
        bool: Whether the two values are the same.
    """
    try:
        return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))
    except (UnicodeEncodeError, TypeError):
        return False


def verify_api_key(
    x_api_key: Optional[str] = Header(default=None),
    authorization: Optional[str] = Header(default=None),
) -> None:
    r"""Reject a request that does not carry one of the configured API keys.

    Installed as a dependency on the application, so it guards the generated
    tool endpoints and ``/health`` alike.

    Args:
        x_api_key (Optional[str]): The ``X-API-Key`` request header.
        authorization (Optional[str]): The ``Authorization`` request header,
            from which a ``Bearer`` scheme is read.

    Raises:
        HTTPException: 401 if the request presents no key, or one that does
            not match.
    """
    if not _API_KEYS:
        # Authentication was switched off on purpose by setting
        # CAMEL_RUNTIME_API_KEY to an empty value.
        return

    presented: Optional[str] = None
    if authorization:
        scheme, _, value = authorization.partition(" ")
        if scheme.lower() == "bearer" and value.strip():
            presented = value.strip()
    if presented is None and x_api_key:
        presented = x_api_key.strip()

    if presented is None:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Pass it via 'Authorization: Bearer "
            "<key>' or 'X-API-Key: <key>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    for key in _API_KEYS:
        if _keys_equal(key, presented):
            return
    raise HTTPException(
        status_code=401,
        detail="Invalid API key.",
        headers={"WWW-Authenticate": "Bearer"},
    )


app = FastAPI(dependencies=[Depends(verify_api_key)])

# global cache for toolkit instances to maintain state across calls
_toolkit_instances: Dict[str, Any] = {}

# track registered endpoints for health check
_registered_endpoints: List[str] = []


@app.get("/health")
async def health_check():
    r"""Health check endpoint that reports loaded toolkits and endpoints."""
    return {
        "status": "ok",
        "toolkits": list(_toolkit_instances.keys()),
        "endpoints": _registered_endpoints,
    }


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal Server Error",
            "error_message": str(exc),
        },
    )


for module_function in modules_functions:
    try:
        # store original module_function as cache key before parsing
        cache_key = module_function

        init_params = dict()
        if "{" in module_function:
            module_function, params = module_function.split("{")
            params = "{" + params
            init_params = json.loads(params)

        module_name, function_name = module_function.rsplit(".", 1)

        logger.info(f"Importing {module_name} and function {function_name}")

        module = importlib.import_module(module_name)
        function = getattr(module, function_name)
        if isinstance(function, type) and issubclass(function, BaseToolkit):
            # use cached instance if available to maintain state across calls
            if cache_key not in _toolkit_instances:
                _toolkit_instances[cache_key] = function(**init_params)
            function = _toolkit_instances[cache_key].get_tools()

        if not isinstance(function, list):
            function = [function]

        for func in function:
            endpoint_name = func.get_function_name()
            _registered_endpoints.append(endpoint_name)

            def make_endpoint(tool):
                r"""Create endpoint with tool captured in closure."""

                def run_tool(data: Dict):
                    r"""Run tool in thread pool to avoid async event loop."""
                    redirect_stdout = data.get('redirect_stdout', False)
                    captured_output = None
                    if redirect_stdout:
                        captured_output = io.StringIO()
                        old_stdout = sys.stdout
                        sys.stdout = captured_output
                    try:
                        response_data = tool.func(
                            *data['args'], **data['kwargs']
                        )
                    finally:
                        if redirect_stdout:
                            sys.stdout = old_stdout
                    if redirect_stdout and captured_output is not None:
                        captured_output.seek(0)
                        output = captured_output.read()
                        return {
                            "output": json.dumps(
                                response_data, ensure_ascii=False
                            ),
                            "stdout": output,
                        }
                    return {
                        "output": json.dumps(response_data, ensure_ascii=False)
                    }

                async def endpoint(data: Dict):
                    # run in thread pool to support sync tools like Playwright
                    loop = asyncio.get_running_loop()
                    return await loop.run_in_executor(
                        _executor, run_tool, data
                    )

                return endpoint

            app.post(f"/{endpoint_name}")(make_endpoint(func))

    except (ImportError, AttributeError) as e:
        logger.error(f"Error importing {module_function}: {e}")


if __name__ == "__main__":
    # reload=False to avoid conflicts with async toolkits (e.g., Playwright)
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
