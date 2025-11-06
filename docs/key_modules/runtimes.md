---
title: "Runtimes"
description: "Flexible, secure, and scalable code execution with CAMEL’s runtime environments: guardrails, Docker, remote, and cloud sandboxes."
icon: server
---

CAMEL’s **runtime module** enables the secure, flexible, and isolated execution of tools and code. Runtimes allow agents to safely run functions in controlled environments—from in-process security checks to Docker isolation and remote/cloud sandboxes.

## What are Runtimes?

<Note type="info" title="Runtime Concept">
  Modern agent systems often require more than a simple interpreter. <b>Runtimes</b> provide safe, scalable execution via guardrails, isolation, or remote/cloud endpoints—ideal for complex or untrusted code.
</Note>

<div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-2 gap-4 my-6">

  <Card icon="shield" title="LLMGuardRuntime">
    <b>Guardrail layer</b> for safe function execution.<br/>
    <ul>
      <li>LLM-based risk scoring (1=safe, 3=unsafe)</li>
      <li>Threshold control for blocking risky calls</li>
      <li>Pre-configured safety system prompt/tool</li>
    </ul>
  </Card>

  <Card icon="docker" title="DockerRuntime / UbuntuDockerRuntime">
    <b>Isolated, reproducible containers</b> via Docker.<br/>
    <ul>
      <li>Sandbox tool execution for safety</li>
      <li>FastAPI server for tool endpoints</li>
      <li>Ubuntu flavor supports .py script execution, env vars, and more</li>
    </ul>
  </Card>

  <Card icon="globe" title="RemoteHttpRuntime">
    <b>Remote, distributed execution</b> on HTTP servers.<br/>
    <ul>
      <li>Tool execution via FastAPI HTTP APIs</li>
      <li>Distribute compute and offload risky code</li>
      <li>Easy integration with remote endpoints</li>
    </ul>
  </Card>

  <Card icon="cloud" title="DaytonaRuntime" className="col-span-1 xl:col-span-3">
    <b>Cloud-managed sandboxing</b> with <a href="https://docs.daytona.io/" target="_blank" rel="noopener">Daytona SDK</a>.<br/>
    <ul>
      <li>Secure remote sandbox per tool</li>
      <li>Upload, run, and manage source code safely</li>
      <li>Automated input/output handling</li>
    </ul>
  </Card>

</div>

## Runtime Interface

All runtimes inherit from <b>BaseRuntime</b>, which defines core methods:
- <code>add(funcs)</code>: Register one or more <code>FunctionTool</code> objects for execution
- <code>reset()</code>: Reset the runtime to its initial state
- <code>get_tools()</code>: List all tools managed by the runtime

## Quick Start Example: RemoteHttpRuntime

<Card icon="zap" title="Remote HTTP Runtime Example" className="my-6">
  Easily run tools in a remote FastAPI-based runtime—great for scaling, isolation, and experimentation.
  <br/><br/>
  ```python
  from camel.runtimes import RemoteHttpRuntime
  from camel.toolkits import MathToolkit

  if __name__ == "__main__":
      runtime = (
          RemoteHttpRuntime("localhost")
          .add(MathToolkit().get_tools(), "camel.toolkits.MathToolkit")
          .build()
      )

      print("Waiting for runtime to be ready...")
      runtime.wait()
      print("Runtime is ready.")

      # There are more tools imported from MathToolkit.
      # For simplicity, we use only "add" tool here
      add = runtime.get_tools()[0]
      print(f"Add 1 + 2: {add.func(1, 2)}")
      # Example output:
      # Add 1 + 2: 3
  ```
</Card>

## Runtime Types: Key Features

<AccordionGroup>
  <Accordion title="LLMGuardRuntime">
    <ul>
      <li>Evaluates risk before executing functions or tool calls (risk scores 1-3)</li>
      <li>Customizable LLM-driven safety logic</li>
      <li>Blocks or allows function execution based on threshold</li>
    </ul>
  </Accordion>
  <Accordion title="DockerRuntime / UbuntuDockerRuntime">
    <ul>
      <li>Runs CAMEL tools/agents in Docker containers for isolation and reproducibility</li>
      <li>UbuntuDocker flavor adds support for full script execution and system-level configuration</li>
      <li>Preconfigures <code>PYTHON_EXECUTABLE</code>, <code>PYTHONPATH</code>, and more for custom envs</li>
    </ul>
  </Accordion>
  <Accordion title="RemoteHttpRuntime">
    <ul>
      <li>Executes registered tools on a remote FastAPI server via HTTP endpoints</li>
      <li>Ideal for distributed, scalable, or cross-server tool execution</li>
    </ul>
  </Accordion>
  <Accordion title="DaytonaRuntime">
    <ul>
      <li>Runs code in a managed, remote cloud sandbox using Daytona SDK</li>
      <li>Uploads user code, executes with input/output capture</li>
      <li>Safety and resource guarantees from cloud provider</li>
    </ul>
  </Accordion>
</AccordionGroup>

## More Examples

You’ll find runnable scripts for each runtime in <b>[examples/runtime](https://github.com/camel-ai/camel/tree/master/examples/runtimes)/</b> in our main repo.  
Each script demonstrates how to initialize and use a specific runtime—perfect for experimentation or production setups.

## Final Note

The runtime system primarily sandboxes <code>FunctionTool</code>-style tool functions.  
For agent-level, dynamic code execution, always consider dedicated sandboxing—such as <b>UbuntuDockerRuntime</b>’s <code>exec_python_file()</code>—for running dynamically generated scripts with maximum isolation and safety.

