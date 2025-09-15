<a id="camel.runtimes.docker_runtime"></a>

<a id="camel.runtimes.docker_runtime.DockerRuntime"></a>

## DockerRuntime

```python
class DockerRuntime(BaseRuntime):
```

A class representing a runtime environment using Docker.
This class automatically wraps functions to be executed
in a Docker container.

**Parameters:**

- **image** (str): The name of the Docker image to use for the runtime.
- **port** (int): The port number to use for the runtime API. (default: :obj: `8000`)
- **remove** (bool): Whether to remove the container after stopping it. ' (default: :obj:`True`)
- **kwargs** (dict): Additional keyword arguments to pass to the Docker client.

<a id="camel.runtimes.docker_runtime.DockerRuntime.__init__"></a>

### __init__

```python
def __init__(
    self,
    image: str,
    port: int = 8000,
    remove: bool = True,
    **kwargs
):
```

<a id="camel.runtimes.docker_runtime.DockerRuntime.mount"></a>

### mount

```python
def mount(self, path: str, mount_path: str):
```

Mount a local directory to the container.

**Parameters:**

- **path** (str): The local path to mount.
- **mount_path** (str): The path to mount the local directory to in the container.

**Returns:**

  DockerRuntime: The DockerRuntime instance.

<a id="camel.runtimes.docker_runtime.DockerRuntime.copy"></a>

### copy

```python
def copy(self, source: str, dest: str):
```

Copy a file or directory to the container.

**Parameters:**

- **source** (str): The local path to the file.
- **dest** (str): The path to copy the file to in the container.

**Returns:**

  DockerRuntime: The DockerRuntime instance.

<a id="camel.runtimes.docker_runtime.DockerRuntime.add_task"></a>

### add_task

```python
def add_task(self, task: TaskConfig):
```

Add a task to run a command inside the container when building.
Similar to `docker exec`.

**Parameters:**

- **task** (TaskConfig): The configuration for the task.

**Returns:**

  DockerRuntime: The DockerRuntime instance.

<a id="camel.runtimes.docker_runtime.DockerRuntime.exec_run"></a>

### exec_run

```python
def exec_run(self, task: TaskConfig):
```

Run a command inside this container. Similar to `docker exec`.

**Parameters:**

- **task** (TaskConfig): The configuration for the task.

**Returns:**

  (ExecResult): A tuple of (exit_code, output)
exit_code: (int):
Exit code for the executed command or `None` if
either `stream` or `socket` is `True`.
output: (generator, bytes, or tuple):
If `stream=True`, a generator yielding response chunks.
If `socket=True`, a socket object for the connection.
If `demux=True`, a tuple of two bytes: stdout and stderr.
A bytestring containing response data otherwise.

<a id="camel.runtimes.docker_runtime.DockerRuntime.build"></a>

### build

```python
def build(self, time_out: int = 15):
```

Build the Docker container and start it.

**Parameters:**

- **time_out** (int): The number of seconds to wait for the container to start. (default: :obj:`15`)

**Returns:**

  DockerRuntime: The DockerRuntime instance.

<a id="camel.runtimes.docker_runtime.DockerRuntime.add"></a>

### add

```python
def add(
    self,
    funcs: Union[FunctionTool, List[FunctionTool]],
    entrypoint: str,
    redirect_stdout: bool = False,
    arguments: Optional[Dict[str, Any]] = None
):
```

Add a function or list of functions to the runtime.

**Parameters:**

- **funcs** (Union[FunctionTool, List[FunctionTool]]): The function or list of functions to add.
- **entrypoint** (str): The entrypoint for the function.
- **redirect_stdout** (bool): Whether to return the stdout of the function. (default: :obj:`False`)
- **arguments** (Optional[Dict[str, Any]]): The arguments for the function. (default: :obj:`None`)

**Returns:**

  DockerRuntime: The DockerRuntime instance.

<a id="camel.runtimes.docker_runtime.DockerRuntime.reset"></a>

### reset

```python
def reset(self):
```

**Returns:**

  DockerRuntime: The DockerRuntime instance.

<a id="camel.runtimes.docker_runtime.DockerRuntime.stop"></a>

### stop

```python
def stop(self, remove: Optional[bool] = None):
```

stop the Docker container.

**Parameters:**

- **remove** (Optional[bool]): Whether to remove the container after stopping it. (default: :obj:`None`)

**Returns:**

  DockerRuntime: The DockerRuntime instance.

<a id="camel.runtimes.docker_runtime.DockerRuntime.ok"></a>

### ok

```python
def ok(self):
```

**Returns:**

  bool: Whether the API Server is running.

<a id="camel.runtimes.docker_runtime.DockerRuntime.wait"></a>

### wait

```python
def wait(self, timeout: int = 10):
```

Wait for the API Server to be ready.

**Parameters:**

- **timeout** (int): The number of seconds to wait. (default: :obj:`10`) (default: 10)

**Returns:**

  bool: Whether the API Server is ready.

<a id="camel.runtimes.docker_runtime.DockerRuntime.__enter__"></a>

### __enter__

```python
def __enter__(self):
```

**Returns:**

  DockerRuntime: The DockerRuntime instance.

<a id="camel.runtimes.docker_runtime.DockerRuntime.__exit__"></a>

### __exit__

```python
def __exit__(
    self,
    exc_type,
    exc_val,
    exc_tb
):
```

Exit the context manager.

<a id="camel.runtimes.docker_runtime.DockerRuntime.docs"></a>

### docs

```python
def docs(self):
```

**Returns:**

  str: The URL for the API documentation.
