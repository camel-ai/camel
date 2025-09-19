<a id="camel.runtimes.configs"></a>

<a id="camel.runtimes.configs.TaskConfig"></a>

## TaskConfig

```python
class TaskConfig(BaseModel):
```

A configuration for a task to run a command inside the container.

Arttributes:
cmd (str or list): Command to be executed
stdout (bool): Attach to stdout. (default: :obj:`True`)
stderr (bool): Attach to stderr. (default: :obj:`True`)
stdin (bool): Attach to stdin. (default: :obj:`False`)
tty (bool): Allocate a pseudo-TTY. (default: :obj:`False`)
privileged (bool): Run as privileged. (default: :obj:`False`)
user (str): User to execute command as. (default: :obj:`""`)
detach (bool): If true, detach from the exec command.
(default: :obj:`False`)
stream (bool): Stream response data. (default: :obj:`False`)
socket (bool): Return the connection socket to allow custom
read/write operations. (default: :obj:`False`)
environment (dict or list): A dictionary or a list of strings in
the following format `__INLINE_CODE_9__` or
`__INLINE_CODE_10____INLINE_CODE_11__None`)
workdir (str): Path to working directory for this exec session.
(default: :obj:`None`)
demux (bool): Return stdout and stderr separately. (default: :obj:
`False`)
