# AnySearch toolkit

`AnySearchToolkit` gives CAMEL agents web search, parallel search, vertical
search discovery, and webpage extraction through the AnySearch HTTP API.
It uses CAMEL's existing `httpx` dependency. Importing the module, creating a
toolkit, and calling `get_tools()` do not send network requests.

## Configuration

Install the local checkout with `pip install -e .` in an activated development
environment. Optionally set `ANYSEARCH_API_KEY` there, then initialize:

```python
from camel.toolkits import AnySearchToolkit

toolkit = AnySearchToolkit(timeout=30.0)
tools = toolkit.get_tools()
```

The constructor accepts `api_key=None`, `anonymous=False`, and `timeout=30.0`.
An explicit API key takes precedence over `ANYSEARCH_API_KEY`. Without a key,
every toolkit operation uses anonymous access. `anonymous=True` explicitly
omits authentication even when an environment key is present:

```python
anonymous_toolkit = AnySearchToolkit(anonymous=True)
```

Anonymous access is limited by the service per IP per day. Its quota is not
the free authenticated account quota. Exhaustion returns an error; the
toolkit never saves credentials from an error response, retries using a
generated key, or changes an invalid authenticated request to anonymous.

Credentials belong in environment variables or constructor arguments, never
in agent prompts or model-visible tool parameters. The example does not load
`.env` files automatically and has no `python-dotenv` dependency.

## Tools and endpoints

All requests use `https://api.anysearch.com`.

| Tool | API request | Behavior |
| --- | --- | --- |
| `anysearch_search_web` | `POST /v1/search` | Search one query, optionally within a vertical. |
| `anysearch_search_batch` | Up to five `POST /v1/search` requests | Run one to five queries concurrently and retain input order. |
| `anysearch_list_domains` | `GET /v1/domains` | Discover currently available search domains. |
| `anysearch_list_subdomains` | `GET /v1/sub-domains` | Discover vertical tags and their parameter definitions. |
| `anysearch_extract_page` | `POST /v1/extract` | Extract content from one public webpage URL. |

Search accepts `query` and optional `max_results`, `tag`, `zone`, `language`,
`params`, and `format`. `max_results` is 1-10; the service default is 10.
`zone` is `cn` or `intl`, and `format` is `json` or `markdown`. `params` holds
parameters defined by the selected vertical. Explicit `None` values use the
same defaults as omitted optional arguments. Blank optional string values and
the model-generated placeholders `"null"` and `"none"` are also omitted;
`zone` and `format` accept valid values regardless of case.

The tool schemas expose `zone` and `format` as enums so models can see the
accepted values. Runtime validation also rejects invalid arguments before
sending an API request.

Batch search accepts the same options, shared across every query. It is a
local parallel operation, not a discounted server batch endpoint. Each query
uses a request and is subject to account or anonymous quotas and rate limits.
Concurrency is bounded by five workers. One query's failure does not discard
the other responses:

```python
result = toolkit.anysearch_search_batch(
    ["CAMEL agent toolkits", "CAMEL multi-agent examples"], max_results=3
)
# {"results": [{"query": "...", "response": {...}}, ...]}
```

List domains before choosing a vertical. Then request subdomains for one to
five selected domains, sent as repeated `domain` query parameters. The toolkit
returns each service response's `data` unchanged, so inspect the live domain
and subdomain directory for the current tags, parameter definitions, required
fields, and source options. Do not assume a fixed directory shape or guess
parameters from an older example.

```python
domains = toolkit.anysearch_list_domains()
directory = toolkit.anysearch_list_subdomains(domains=["code"])
# Inspect domains["data"] and directory["data"] before selecting a tag.
```

For example, the documented `code.doc` vertical uses a `library` parameter:

```python
result = toolkit.anysearch_search_web(
    "React useEffect cleanup", tag="code.doc", params={"library": "react"}
)
```

This illustrates the API shape; verify that the tag and accepted library
are present in the current directory before making the request.

Extraction sends only `{"url": "https://..."}`. The API accepts public HTTP
or HTTPS pages, including HTML/XHTML, text, JSON, and Markdown. It is not a
PDF, image, audio, or video parser. The UTF-8 JSON request body must fit
within 16 KiB. Text or HTML extraction may be truncated by the service at
50,000 characters; callers must not assume the returned content is complete.

## Responses, errors, and timeouts

Successful single requests return a normalized envelope with the service's
`data` unchanged:

```json
{"code": 0, "message": "success", "data": {}}
```

The optional `request_id` is included when the service returns a safe value.
`data` is endpoint-specific. Search output can depend on `format`, while
directory and extraction results have their own structures. The toolkit does
not invent a shared `data` schema or discard citation URLs.

Failures return `{"error": "..."}` and, when available, safe `status_code`,
`request_id`, or `retry_after` metadata (integer seconds). They include
invalid local inputs, transport errors, non-success HTTP responses,
malformed JSON, and service errors. Raw response bodies and authentication
headers are not exposed in
errors. In particular, anonymous HTTP 402 responses can include generated
credentials, so their payloads are not forwarded to agents or logs.

There are no automatic retries. Callers decide how to handle quota failures
or `retry_after`; batch requests may finish with a mix of successes and
failures. A timeout is a per-request HTTP I/O timeout, not a strict deadline
for an entire batch. `timeout=None` disables the HTTP timeout and is usually
unsuitable for an unattended agent.

The synchronous methods use HTTPX and CAMEL `FunctionTool` registration.
CAMEL's `FunctionTool.async_call()` runs synchronous tools in its executor,
so the same functions can be used from asynchronous agents. Network methods
manage HTTP timeouts directly rather than relying on a background-thread
wrapper that could replace a dictionary result with a timeout string.

## Runnable example

From the repository root, choose one operation explicitly. Each operation
invocation below makes live requests; `--help` only displays usage, and no
request runs when the example is imported. With no `ANYSEARCH_API_KEY`, all
operations use anonymous access. Use `--anonymous-access` with any operation
to omit authentication even when an environment key is present. The older
`--anonymous QUERY` search form also remains available.

```bash
python examples/toolkits/anysearch_toolkit_example.py --help
python examples/toolkits/anysearch_toolkit_example.py --domains
python examples/toolkits/anysearch_toolkit_example.py --search "CAMEL AI"
python examples/toolkits/anysearch_toolkit_example.py --batch "CAMEL AI" "agent tools" --max-results 3
python examples/toolkits/anysearch_toolkit_example.py --directory code
python examples/toolkits/anysearch_toolkit_example.py --extract https://www.camel-ai.org/
python examples/toolkits/anysearch_toolkit_example.py --domains --anonymous-access
python examples/toolkits/anysearch_toolkit_example.py --anonymous "CAMEL AI"
```

After inspecting the domain and subdomain directories, a Bash vertical-search
invocation is:

```bash
python examples/toolkits/anysearch_toolkit_example.py --vertical "React useEffect cleanup" --tag code.doc --params '{"library":"react"}'
```

Shell JSON quoting differs across platforms; `--params` must reach Python as
one JSON object. Prefer the direct Python example above if your shell changes
the quote characters. The CLI logs at most 6,000 characters per result; the
toolkit itself returns the complete service response.

For a model-driven example, also set `DEEPSEEK_API_KEY`. The optional
`DEEPSEEK_MODEL` defaults to `deepseek-chat`; `DEEPSEEK_API_BASE_URL` can set
the model endpoint. The example uses CAMEL's native DeepSeek model backend:

```bash
python examples/toolkits/anysearch_toolkit_example.py --agent "Search for CAMEL AI and summarize its purpose with source URLs."
```

The agent is limited to five model iterations. It may make multiple model
and search requests; a single CLI invocation is not a single-request quota
guarantee. The example reports each tool's success or failure and exits with
a nonzero status if a tool fails, even if the model produces an answer.
Direct tool modes do not need a model API key.

## Development and maintenance

The implementation lives in `camel/toolkits/anysearch_toolkit.py`, is
exported from `camel.toolkits`, and registers five public functions through
`get_tools()`. Keep API credentials and construction-only settings outside
their function schemas. `params` intentionally permits a dictionary of
vertical-specific fields, so inspect generated schemas when changing its
typing; CAMEL may disable strict schema mode for open mappings.

Run the focused offline tests and style checks from the repository root:

```bash
pytest test/toolkits/test_anysearch_toolkit.py
ruff check camel/toolkits/anysearch_toolkit.py examples/toolkits/anysearch_toolkit_example.py test/toolkits/test_anysearch_toolkit.py
ruff format --check camel/toolkits/anysearch_toolkit.py examples/toolkits/anysearch_toolkit_example.py test/toolkits/test_anysearch_toolkit.py
```

Tests should mock HTTP requests and cover explicit key precedence, anonymous
headers, optional `None`, request parameters, both directory endpoints, batch
order and partial errors, extraction validation, malformed responses, timeouts,
quota failures, safe error metadata, and `FunctionTool` schemas and calls.
No API key or network access should be necessary for those tests. Real
service checks use the CLI explicitly and should record the operation and
outcome without storing credentials or unredacted error bodies.

When the API changes, update request validation, response handling, mocked
fixtures, docstrings, and this document together. Recheck the live directory
for vertical-specific parameters. Preserve bounded parallelism, input order,
absence of automatic retries, and the separation between anonymous and
authenticated access.

Official references:

- [Authentication](https://anysearch.com/docs/auth)
- [Search API](https://anysearch.com/docs/api-endpoints/v1-search)
- [Vertical directory](https://anysearch.com/docs/api-endpoints/v1-sub-domains)
- [Extract API](https://anysearch.com/docs/api-endpoints/v1-extract)
