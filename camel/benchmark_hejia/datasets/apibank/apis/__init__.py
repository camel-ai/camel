from .api import API

import os
import importlib

# Get the directory path of the "apis" folder
apis_dir = os.path.dirname(os.path.abspath(__file__))

# Get a list of all the files in the "apis" folder
api_files = [f[:-3] for f in os.listdir(apis_dir) if f.endswith(".py") and f != "__init__.py"]

# Import all classes in the files in the "apis" folder
for api_file in api_files:
    try:
        module = importlib.import_module(f".{api_file}", package="apis")
        globals().update({k: v for k, v in module.__dict__.items() if not k.startswith("__")})
    except ImportError:
        # Handle ImportError, if necessary
        pass
