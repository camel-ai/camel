# Runtime

## 1. Concept
The runtime module in CAMEL allows functions and tools to be executed in 
controlled environments, enabling safe and isolated execution of code.
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
All runtimes inherit from the BaseRuntime abstract class, which defines the following core methods:

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


### 2.4 `UbuntuDockerRuntime`

### 2.5 `RemoteHttpRuntime`

The RemoteHttpRuntime facilitates the execution of functions on a separate,
remote HTTP server. 
This is particularly useful for distributing computational workloads, 
accessing resources or services that are only available on a specific 
server, or integrating CAMEL agents with existing microservices or 
specialized remote workers.

### 2.6 `DaytonaRuntime`



## 3. Get Started

## 4. More Examples
 