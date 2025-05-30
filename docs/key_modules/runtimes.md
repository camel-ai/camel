## 1. Concept
The runtime module in CAMEL allows functions and tools to be executed in 
controlled environments, enabling the safe and isolated execution of code.
Modern AI systems, especially those involving autonomous agents, often 
require more than just a simple Python interpreter. They may need to:

- Execute code with security checks to prevent malicious actions.
- Run tasks in isolated environments to manage dependencies or enhance 
security (e.g., using Docker).
- Distribute computational load or access specialized resources by executing 
functions on remote servers.
- Utilize sophisticated configuration management for various components.

The `camel.runtime` module addresses these needs by providing a collection of 
runtime classes and supporting utilities. Each runtime offers a different 
strategy for code or function execution, catering to various use cases within 
the CAMEL ecosystem.

## 2. Types
Runtimes offer flexibility, isolation, and scalability by encapsulating 
various execution contexts—such as local containers, cloud sandboxes, 
remote servers, or guarded environments.
Each runtime implementation provides a standardized interface for adding 
tools, executing commands, and managing the execution lifecycle.

### 2.1 The Base Runtime: `BaseRuntime`
All runtimes inherit from the BaseRuntime abstract class, which defines the 
following core methods:

- `add(funcs)`: Registers one or more FunctionTool objects for execution

- `reset()`: Resets the runtime environment to its initial state

- `get_tools()`: Returns the list of tools managed by the runtime

### 2.2 `LLMGuardRuntime`
The `LLMGuardRuntime` is a runtime environment designed to evaluate 
the potential risks associated with executing functions and tools, 
particularly those that might be dynamically called by AI agents 
(e.g., tool calls that write codes).
`LLMGuardRuntime` leverages a customizable LLM to
perform this risk assessment.

**Key Features:**
- Risk scores from 1 (safe) to 3 (dangerous)
- Threshold control for execution permission
- Pre-configured system prompt + structured tool for safety

### 2.3 `DockerRuntime`
The `DockerRuntime` provides a mechanism to
execute CAMEL agents or arbitrary tasks
within isolated Docker containers. This approach is highly beneficial
for managing complex dependencies, 
ensuring reproducibility of experiments or agent behavior, 
and enhancing security by sandboxing execution.

**Key Features**
- FastAPI server for tool exposure
- Automatic container lifecycle management via Python interface

### 2.4 `UbuntuDockerRuntime`
A specialization of `DockerRuntime` optimized for Ubuntu containers. 
Adds system package installation, Python version checks, 
and support for full script execution.

**Key Features**
- Preconfigures environment variables like `PYTHON_EXECUTABLE` and `PYTHONPATH`
- Supports full `.py` script execution with `exec_python_file()`
- Maintains all capabilities of DockerRuntime.

### 2.5 `RemoteHttpRuntime`
The `RemoteHttpRuntime` facilitates the execution of functions on a separate,
remote HTTP server. 

**Key Features**
- Enables remote execution of tools via simple HTTP APIs
- Built on FastAPI for easy integration and rapid deployment
 of HTTP-based function execution endpoints

### 2.6 `DaytonaRuntime`
`DaytonaRuntime` uses the official daytona_sdk to create sandboxes and run user
functions inside them securely.
Each tool is uploaded as source code and executed with controlled input/output
handling.

**Key Features**
- Uploads and runs source code remotely
- Cloud-managed runtime with safety guarantees

## 3. Get Started
We'll use `RemoteHttpRuntime` as a quick examples of how to use 
`runtime` module.

A runtime can be initialized with the following code. Here we use
`MathToolkit` as an example for our tools. You can use any arbitrary tools as
long as they follow the `FunctionTool` type defined by CAMEL (see [tools](
./tools.md) 
module document for more details.)
```
from camel.runtime import RemoteHttpRuntime
from camel.toolkits import MathToolkit

if __name__ == "__main__":
    runtime = (
        RemoteHttpRuntime("localhost")
        .add(MathToolkit().get_tools(), "camel.toolkits.MathToolkit")
        .build()
    )
    
    # It might take sometime for the runtime to start
    print("Waiting for runtime to be ready...")
    runtime.wait()
    print("Runtime is ready.")
    # Example Output:
    # Waiting for runtime to be ready...
    # Runtime is ready.
```


The tools can then be called using the code below, 
following the same syntax as normal tool calls without a runtime.

```
    # There are more tools imported from MathToolkit. 
    # For simplicity, we use only "add" tool here
    add = runtime.get_tools()[0]  
    print(f"Add 1 + 2: {add.func(1, 2)}")
    
    # Example Output:
    # Add 1 + 2: 3
```

## 4. More Examples
Additional runtime usage examples can be found under the `examples/runtime/` 
directory in our main repository. Each script demonstrates how to initialize 
and use a specific runtime in CAMEL. These examples are simple, 
self-contained, and can serve as starting points for real use cases.

## 5. Final Note
Currently, the runtime system is mainly designed to sandbox registered tool 
functions only. If other parts of your agent involve 
risky execution (e.g., direct code generation
and execution), you should consider handling sandboxing logic separately.

**Exception**: UbuntuDockerRuntime supports full Python script execution 
through exec_python_file(). This makes it suitable for broader agent-level 
sandboxing beyond `FunctionTool`, such as executing dynamically generated code
within a controlled container environment.
