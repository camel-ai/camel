---
title: "Interpreters"
description: "Execute code safely and flexibly with CAMEL’s suite of interpreters: local, isolated, and cloud-based execution environments."
icon: terminal
---

Interpreters allow CAMEL agents to **execute code snippets** in various secure and flexible environments—from local safe execution to isolated Docker containers and managed cloud sandboxes.

## What are Interpreters?

<Note type="info" title="Interpreter Concept">
  Interpreters empower agents to run code dynamically—enabling evaluation,
  testing, task automation, and rich feedback loops. Choose your interpreter
  based on trust, isolation, and supported languages.
</Note>

<div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 my-6">

{" "}
<Card icon="python" title="Internal Python Interpreter">
  <b>Fast, local, safe</b> execution for trusted Python code within the agent
  process.
  <br />
  <small>
    <b>Best for:</b> Trusted code, quick Python evaluation.
  </small>
</Card>

{" "}
<Card icon="code" title="Subprocess Interpreter">
  <b>Isolated execution</b> in a subprocess. Supports Bash, Python, shell
  scripts.
  <br />
  <small>
    <b>Best for:</b> Shell commands, scripts, process isolation.
  </small>
</Card>

{" "}
<Card icon="docker" title="Docker Interpreter">
  <b>Fully sandboxed</b> in Docker containers.
  <br />
  <small>
    <b>Best for:</b> Untrusted code, dependency isolation, safe experimentation.
  </small>
  <br />
  <a href="https://docs.docker.com/get-docker/" target="_blank" rel="noopener">
    Install Docker
  </a>
</Card>

{" "}
<Card icon="book-open" title="IPython Interpreter">
  <b>Interactive, stateful</b> execution via Jupyter/IPython kernel.
  <br />
  <small>
    <b>Best for:</b> Multi-step reasoning, persistent variables, rich outputs.
  </small>
</Card>

{" "}
<Card icon="cloud" title="E2B Interpreter">
  <b>Cloud-based sandboxing</b> for scalable, secure remote execution.
  <br />
  <small>
    <b>Best for:</b> Managed, scalable tasks. No local setup needed.
  </small>
  <br />
  <a href="https://e2b.dev/docs" target="_blank" rel="noopener">
    E2B Docs
  </a>
</Card>

</div>

---

<Card icon="python" title="Internal Python Interpreter" className="my-6">
  <b>Fast, local, and safe</b>—executes trusted Python code directly within the CAMEL agent process.<br/>
  <b>Note:</b> Only expressions (not statements) are allowed in strict safe mode; for output, your code should evaluate to a string.
  <br/><br/>
  ```python
  from camel.interpreters import InternalPythonInterpreter

# Initialize the interpreter

interpreter = InternalPythonInterpreter()

# Code to execute (should evaluate to a string)

python_code = "'Hello from InternalPythonInterpreter!'"

# Run code

result_str = interpreter.run(code=python_code, code_type="python")
print(f"Result: {result_str}")

````
</Card>

<Card icon="code" title="Subprocess Interpreter" className="my-6">
Execute shell commands or scripts in a separate process for isolation and flexibility.<br/>
Supports multiple languages, including Bash and Python.
<br/><br/>
```python
from camel.interpreters import SubprocessInterpreter

interpreter = SubprocessInterpreter()
shell_command = "echo 'Hello from SubprocessInterpreter!'"

result_str = interpreter.run(code=shell_command, code_type="bash")
print(f"Result: {result_str.strip()}")
````

</Card>

<Card icon="docker" title="Docker Interpreter" className="my-6">
  Provides full isolation—code runs in a Docker container, protecting your host system and supporting any dependencies.<br/>
  <b>Requires Docker installed.</b>
  <br/>
  <a href="https://docs.docker.com/get-docker/" target="_blank">Install Docker</a>
  <br/><br/>
  ```python
  from camel.interpreters import DockerInterpreter

interpreter = DockerInterpreter()
python_code_in_docker = "print('Hello from DockerInterpreter!')"

result_str = interpreter.run(code=python_code_in_docker, code_type="python")
print(f"Result: {result_str.strip()}")

````
</Card>

<Card icon="book-open" title="IPython Interpreter (JupyterKernel)" className="my-6">
Interactive, stateful execution in a Jupyter-like Python kernel—maintains session state and supports rich outputs.
<br/><br/>
```python
from camel.interpreters import JupyterKernelInterpreter

interpreter = JupyterKernelInterpreter(
    require_confirm=False, print_stdout=True, print_stderr=True
)

python_code_in_jupyter_kernel = "print('Hello from JupyterKernelInterpreter!')"
result = interpreter.run(code=python_code_in_jupyter_kernel, code_type="python")
print(result)
````

</Card>

<Card icon="cloud" title="E2B Interpreter (Cloud Sandbox)" className="my-6">
  Run code in a secure, scalable, cloud-based environment—no local setup needed, great for running untrusted or complex code.<br/>
  <a href="https://e2b.dev/docs" target="_blank">E2B Documentation</a>
  <br/><br/>
  ```python
  from camel.interpreters import E2BInterpreter

interpreter = E2BInterpreter()
python_code_in_e2b = "print('Hello from E2BInterpreter!')"
result = interpreter.run(code=python_code_in_e2b, code_type="python")
print(result)

```
</Card>

<AccordionGroup>
<Accordion title="Best Practices">
  <ul>
    <li>Use <b>InternalPythonInterpreter</b> only for trusted and simple Python code.</li>
    <li><b>Subprocess</b> and <b>Docker</b> interpreters are better for code isolation and dependency management.</li>
    <li>Prefer <b>Docker</b> for any untrusted code or when extra libraries are needed.</li>
    <li><b>E2B Interpreter</b> is ideal for scalable, managed, and safe cloud execution—no local risk.</li>
    <li>For interactive, multi-step logic, leverage <b>JupyterKernelInterpreter</b> for persistent session state.</li>
    <li>Always validate and sanitize user inputs if agents dynamically construct code for execution.</li>
  </ul>
</Accordion>
<Accordion title="Troubleshooting & Tips">
  <ul>
    <li>If Docker isn’t working, verify your Docker daemon is running and you have the correct permissions.</li>
    <li>For E2B, check API key and account limits if code doesn’t execute.</li>
    <li>Long-running scripts are best managed in <b>Subprocess</b> or <b>Docker</b> interpreters with timeout controls.</li>
    <li>Use session resets (where supported) to avoid cross-task state bleed in Jupyter/IPython interpreters.</li>
  </ul>
</Accordion>
</AccordionGroup>
```
