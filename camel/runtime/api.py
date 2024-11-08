from typing import Dict
from fastapi import FastAPI, Request
import importlib
import sys
import uvicorn
from camel.toolkits import BaseToolkit

modules_functions = sys.argv[1:]

print(f"Modules and functions: {modules_functions}")

app = FastAPI()

for module_function in modules_functions:
    try:
        module_name, function_name = module_function.rsplit(".", 1)
        print(f"Importing {module_name} and function {function_name}")
        module = importlib.import_module(module_name)
        function = getattr(module, function_name)
        if isinstance(function, type) and issubclass(function, BaseToolkit):
            function = function().get_tools()
        
        if isinstance(function, list):
            for func in function:
                @app.post(f"/{func.get_function_name()}")
                async def dynamic_function(data: Dict, func=func):
                    response_data = func.func(*data['args'], **data['kwargs'])
                    return response_data
            continue
        else:
            @app.post(f"/{function_name}")
            async def dynamic_function(data: Dict, func=function):
                response_data = func.func(*data['args'], **data['kwargs'])
                return response_data

    except (ImportError, AttributeError) as e:
        print(f"Error importing {module_function}: {e}")

if __name__ == "__main__":
    uvicorn.run("__main__:app", host="0.0.0.0", port=8000, reload=True)
