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
import importlib
import io
import json
import logging
import os
import sys
from typing import Any, Dict, List

import uvicorn
from fastapi import FastAPI, Request
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

app = FastAPI()

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
