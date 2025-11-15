import json
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import create_model
from typing_extensions import Annotated

from tau2.environment.environment import Environment
from tau2.environment.toolkit import get_tool_signatures


class EnvironmentServer:
    """
    A FastAPI server that exposes the tools of an Environment as HTTP endpoints.
    """

    def __init__(self, environment: Environment):
        """
        Initialize the server with an environment.

        Args:
            environment: The environment to serve
        """
        self.environment = environment
        self.app = FastAPI(
            title=f"Environment: {environment.get_domain_name()}",
            description=self._format_description(environment.get_policy()),
            version="1.0.0",
            # Add OpenAPI customization
            openapi_tags=[
                {"name": "Tools", "description": "Available tools in this environment"},
                {
                    "name": "User Tools",
                    "description": "User-defined tools in this environment",
                },
            ],
            # Add custom metadata
            openapi_url="/api/openapi.json",
            docs_url="/docs",
            redoc_url="/redoc",
        )
        self._setup_routes()

    def _format_description(self, policy: str) -> str:
        """Format the API description with markdown for better ReDoc rendering"""
        import re

        # Look for sections using regex
        sections = {}
        for section_name in ["main_policy", "tech_support_policy"]:
            pattern = f"<{section_name}>(.*?)</{section_name}>"
            match = re.search(pattern, policy, re.DOTALL)
            if match:
                sections[section_name] = match.group(1).strip()

        # If no sections found, return original format
        if not sections:
            return f"""
{policy}

## Tools

This environment provides several tools that can be used via API endpoints. Each tool is exposed as a POST endpoint under `/tools/`.

### Authentication

No authentication is required for this API.

### Response Format

All successful responses will return the tool's output directly. Errors will return a 400 status code with an error message.
"""

        # Format the description with sections
        description = []

        # Add main policy if it exists
        if "main_policy" in sections:
            description.append(sections["main_policy"])

        # Add other sections as subsections
        for section_name, content in sections.items():
            if section_name != "main_policy":
                description.append(f"\n## {section_name.replace('_', ' ').title()}\n")
                description.append(content)

        # Add the tools section
        description.append("""

## Tools

This environment provides several tools that can be used via API endpoints. Each tool is exposed as a POST endpoint under `/tools/`.

### Authentication

No authentication is required for this API.

### Response Format

All successful responses will return the tool's output directly. Errors will return a 400 status code with an error message.
""")

        return "\n".join(description)

    def _setup_routes(self):
        """Set up routes for each Agent tool and user tool in the environment"""
        # Set up regular tools
        tool_signatures = get_tool_signatures(self.environment.tools)
        self._setup_tool_routes(tool_signatures, "tools")

        # Set up user tools if they exist
        if self.environment.user_tools is not None:
            user_tool_signatures = get_tool_signatures(self.environment.user_tools)
            self._setup_tool_routes(user_tool_signatures, "user_tools")

    def _setup_tool_routes(self, tool_signatures: dict, route_prefix: str):
        """Helper method to set up routes for a set of tools"""
        for name, signature in tool_signatures.items():
            # Create a Pydantic model for the tool's parameters
            if signature.params:
                fields = {}
                for param_name, param_schema in signature.params["properties"].items():
                    # Convert JSON schema types to Python types
                    python_type = str  # default type
                    if param_schema.get("type") == "number":
                        python_type = float
                    elif param_schema.get("type") == "integer":
                        python_type = int
                    elif param_schema.get("type") == "boolean":
                        python_type = bool

                    fields[param_name] = (Annotated[python_type, None], ...)

                RequestModel = create_model(
                    f"{name.title()}Request",
                    **fields,
                    __doc__=f"Request model for the {name} tool",
                )
            else:
                RequestModel = create_model(
                    f"{name.title()}Request",
                    __doc__=f"Request model for the {name} tool",
                )

            # Create the route with enhanced documentation
            summary = f"{name.replace('_', ' ').title()}"

            @self.app.post(
                f"/{route_prefix}/{name}",
                response_model=Any,
                description=self._format_tool_description(
                    signature.doc, signature.returns, route_prefix == "user_tools"
                ),
                name=name,
                tags=["User Tools" if route_prefix == "user_tools" else "Tools"],
                summary=summary,
            )
            async def tool_endpoint(
                request: RequestModel,  # type: ignore
                tool_name: str = name,
            ) -> Any:
                try:
                    if route_prefix == "user_tools":
                        result = self.environment.use_user_tool(
                            tool_name=tool_name, **request.model_dump()
                        )
                    else:
                        result = self.environment.use_tool(
                            tool_name=tool_name, **request.model_dump()
                        )
                    return result
                except Exception as e:
                    raise HTTPException(status_code=400, detail=str(e))

    def _format_tool_description(
        self, doc: str, returns: Optional[dict] = None, is_user_tool: bool = False
    ) -> str:
        """Format tool documentation for better ReDoc rendering"""
        import re

        # Extract content between triple quotes using regex
        match = re.search(r'"""(.*?)"""', doc, re.DOTALL)
        if match:
            doc = match.group(1).strip()

        description = f"""
{"(User Tool) " if is_user_tool else ""}{doc}

### Response Format
The response will be the direct output of the tool execution.
"""

        if returns and "properties" in returns:
            # Get the first (and usually only) property's info
            return_info = next(iter(returns["properties"].values()))

            description += "\n<details><summary>Response Schema</summary>\n\n```json\n"
            description += json.dumps(return_info, indent=2)
            description += "\n```\n</details>\n"

        description += """
### Errors
- Returns 400 if the tool execution fails
- Returns 422 if the request parameters are invalid
"""
        return description

    def get_app(self) -> FastAPI:
        """
        Get the FastAPI application.

        Returns:
            The FastAPI application
        """
        return self.app

    def run(self, host: str = "127.0.0.1", port: int = 8004):
        """
        Run the FastAPI server.

        Args:
            host: The host to bind to
            port: The port to bind to
        """
        import uvicorn

        uvicorn.run(self.app, host=host, port=port)
