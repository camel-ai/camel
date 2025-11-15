
# Agent Developer Guide

## Understanding the Environment

To develop an agent for a specific domain, you first need to understand the domain's policy and available tools. Start by running the environment server for your target domain:

```bash
tau2 domain <domain>
```

This will start a server and automatically open your browser to the API documentation page (ReDoc). Here you can:
- Review the available tools (API endpoints) for the domain
- Understand the policy requirements and constraints
- Test API calls directly through the documentation interface

## Developing an Agent

Implement the `LocalAgent` class in `src/tau2/agent/base.py`

Register your agent in `src/tau2/agent/registry.py`
```python
registry.register_agent(MyAgent, "my_agent")
```

## Testing Your Agent
You can now use the command:
```bash
tau2 run \
  --domain <domain> \
  --agent my_agent \
  --agent-llm <llm_name> \
  --user-llm <llm_name> \
  ...
```