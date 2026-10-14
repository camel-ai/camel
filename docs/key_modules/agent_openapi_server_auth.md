# ChatAgentOpenAPIServer authentication and ownership

All seven `/v1/agents` endpoints now require a Bearer token configured by the
operator. Without a configured key mapping the API returns `401`, before any
agent, model, or registered tool can be invoked. Missing/invalid credentials
receive `WWW-Authenticate: Bearer`. Credentials in query strings are not used.

## Configure identities

Generate high-entropy tokens with a secret manager or
`secrets.token_urlsafe(32)`, store them outside source control, and distribute
them securely to the intended clients. Tokens must be at least 32 characters.
For example, export `CAMEL_ALICE_TOKEN` and `CAMEL_BOB_TOKEN` securely before
starting this application:

```python
import os

from camel.services.agent_openapi_server import ChatAgentOpenAPIServer

server = ChatAgentOpenAPIServer(
    api_keys={
        os.environ['CAMEL_ALICE_TOKEN']: 'alice',
        os.environ['CAMEL_BOB_TOKEN']: 'bob',
    },
)
app = server.get_app()
```

Clients send `Authorization: Bearer <their-token>` on every request. Use TLS
for network deployments; a Bearer credential grants access to its configured
identity. Do not put tokens in URLs or logs. The examples in
`examples/services/agent_openapi_server.py` use `CAMEL_SERVER_API_KEY` to configure
the in-process example client and server.

## Owner isolation

- `/init` records the authenticated identity as the new agent's owner. Request
  fields cannot select or override the owner.
- `/list_agent_ids` includes only that identity's agents.
- `/step`, `/astep`, `/history`, `/reset`, and `/delete` check ownership before
  using the agent. An unknown or another user's agent ID receives the same
  `404` response. `/init` cannot take over another identity's existing ID.
- Concurrent initialization rechecks ownership before storing a constructed
  agent. Deletion removes both the agent and its ownership metadata.
- Multiple tokens can map to one stable owner identity for key rotation.
  Different identities remain isolated even when they know another agent ID.

## Migration and limits

This intentionally changes unauthenticated deployments: supply `api_keys` and
update every client to send a Bearer header. Directly inserting agents into
`server.agents` does not assign ownership or make them visible to API callers;
initialize agents through the authenticated API instead. Agents and ownership
are in process memory, as before; this is not cross-worker persistent storage.

The tool registry is still an operator-controlled allowlist. Authentication
does not sandbox the tools or add per-owner tool scopes, quotas, or network
isolation. Only register tools appropriate for identities receiving keys, and
use an isolated execution environment and approval controls for host tools.

Run the offline API regression suite without model calls:

```bash
python -m pytest test/services/test_agent_openapi_server_auth.py test/services/test_agent_openapi_server.py -q -m "not model_backend"
```
