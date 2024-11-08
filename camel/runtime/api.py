import json
from typing import Dict
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import importlib
import sys
import uvicorn
from camel.toolkits import BaseToolkit
import io
import sys

modules_functions = sys.argv[1:]

print(f"Modules and functions: {modules_functions}")

app = FastAPI()


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
        init_params = dict()
        if "(" in module_function:
            module_function, params = module_function.split("(")
            params = f"dict({params}"
            init_params = eval(params)

        module_name, function_name = module_function.rsplit(".", 1)
        
        print(f"Importing {module_name} and function {function_name}")
        
        module = importlib.import_module(module_name)
        function = getattr(module, function_name)
        if isinstance(function, type) and issubclass(function, BaseToolkit):
            function = function(**init_params).get_tools()

        if not isinstance(function, list):
            function = [function]
            
        for func in function:
            @app.post(f"/{func.get_function_name()}")
            async def dynamic_function(data: Dict, func=func):
                return_output = data.get('return_stdout', False)
                if return_output:
                    sys.stdout = io.StringIO()
                response_data = func.func(*data['args'], **data['kwargs'])
                if return_output:
                    sys.stdout.seek(0)
                    output = sys.stdout.read()
                    sys.stdout = sys.__stdout__
                    return {"output": json.dumps(response_data), "stdout": output}
                return {"output": json.dumps(response_data)}

    except (ImportError, AttributeError) as e:
        print(f"Error importing {module_function}: {e}")
        

if __name__ == "__main__":
    uvicorn.run("__main__:app", host="0.0.0.0", port=8000, reload=True)
