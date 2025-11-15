from copy import deepcopy
from typing import Callable, Optional

from loguru import logger
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.theme import Theme

from tau2.config import DEFAULT_LLM_ENV_INTERFACE, DEFAULT_LLM_ENV_INTERFACE_ARGS
from tau2.data_model.message import (
    AssistantMessage,
    Message,
    SystemMessage,
    UserMessage,
)
from tau2.environment.environment import Environment
from tau2.utils.llm_utils import generate

SYSTEM_PROMPT = """
# Instruction
You are an query interface agent that helps the developer interact with a database.
You have access to tools that can be used to query the database.
You will receive a query from the developer.
You will need to make the appropriate tool calls to the database and return the result.
If the you cannot answer the question, return a message explaining why and how to modify the query.
You can also ask clarifying questions to the developer to help you answer the question.
When making a tool call, always return valid JSON only.
""".strip()


class InterfaceAgent:
    def __init__(
        self,
        environment: Environment,
        llm: Optional[str] = DEFAULT_LLM_ENV_INTERFACE,
        llm_args: Optional[dict] = DEFAULT_LLM_ENV_INTERFACE_ARGS,
    ):
        """
        Initialize the InterfaceAgent.
        """
        self.messages = []
        self.environment = environment
        self.llm = llm
        self.llm_args = deepcopy(llm_args) if llm_args is not None else {}

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def respond(
        self,
        message: str,
        message_history: Optional[list[Message]] = None,
    ) -> tuple[AssistantMessage, list[Message]]:
        """
        Respond to a user message.
        """
        if message_history is None:
            message_history = []
        system_message = SystemMessage(role="system", content=self.system_prompt)
        user_message = UserMessage(role="user", content=message)
        message_history.append(user_message)
        messages = [system_message] + message_history
        assistant_message = generate(
            model=self.llm,
            tools=self.environment.get_tools(),
            messages=messages,
            **self.llm_args,
        )
        while assistant_message.is_tool_call():
            message_history.append(assistant_message)
            for tool_call in assistant_message.tool_calls:
                tool_message = self.environment.get_response(tool_call)
                message_history.append(tool_message)
            messages = [system_message] + message_history
            assistant_message = generate(
                model=self.llm,
                tools=self.environment.get_tools(),
                messages=messages,
                **self.llm_args,
            )
        message_history.append(assistant_message)
        return assistant_message, message_history

    def set_seed(self, seed: int):
        """Set the seed for the LLM."""
        if self.llm is None:
            raise ValueError("LLM is not set")
        cur_seed = self.llm_args.get("seed", None)
        if cur_seed is not None:
            logger.warning(f"Seed is already set to {cur_seed}, resetting it to {seed}")
        self.llm_args["seed"] = seed


def get_interface_agent(get_environment: Callable[[], Environment]) -> InterfaceAgent:
    """Get an interface agent that can be used to interact with the environment."""
    return InterfaceAgent(get_environment())


def main():
    """
    Main function to run the interface agent in an interactive CLI mode.
    Allows users to interact with different domain environments through the interface agent.
    Commands:
        :q - quit the program
        :d - change domain
        :n - start new session
    """
    from tau2.registry import registry

    # Setup rich console with custom theme
    theme = Theme(
        {
            "info": "cyan",
            "warning": "yellow",
            "error": "bold red",
            "success": "bold green",
            "prompt": "bold cyan",
            "domain": "bold blue",
            "command": "bold magenta",
        }
    )
    console = Console(theme=theme)

    # Get available domains
    available_domains = registry.get_domains()
    default_domain = "airline"

    if default_domain not in available_domains:
        console.print(f"[error]Error:[/] Default domain '{default_domain}' not found!")
        return

    # Welcome message
    console.print(
        Panel.fit(
            "[success]Welcome to the Interface Agent CLI![/]\n"
            + "Type [command]:q[/] to quit, [command]:d[/] to change domain, [command]:n[/] to start new session",
            title="Interface Agent",
            border_style="blue",
        )
    )

    def change_domain(console: Console) -> str:
        """Helper function to handle domain selection"""
        console.print("\n[info]Available domains:[/]")
        for d in available_domains:
            console.print(f"  • [domain]{d}[/]")

        while True:
            domain = (
                Prompt.ask(
                    "\n[prompt]Enter domain name[/]",
                    console=console,
                    default=default_domain,
                )
                .strip()
                .lower()
            )

            if domain == ":q":
                return None

            if domain not in available_domains:
                console.print(f"[error]Error:[/] '{domain}' is not a valid domain.")
                continue

            return domain

    def init_session(domain: str) -> tuple[InterfaceAgent, list[Message]]:
        """Helper function to initialize or reset a session"""
        with console.status(f"[info]Initializing {domain} session...[/]"):
            get_env = registry.get_env_constructor(domain)
            interface_agent = get_interface_agent(get_env)
        console.print(
            Panel(
                f"[success]Connected to [domain]{domain}[/success] domain\n"
                + "Type [command]:q[/] to quit, [command]:d[/] to change domain, [command]:n[/] to start new session",
                border_style="green",
            )
        )
        return interface_agent, []

    current_domain = default_domain
    try:
        while True:
            try:
                interface_agent, message_history = init_session(current_domain)

                while True:
                    try:

                        def get_prompt_text() -> str:
                            """Helper function to create the prompt text with commands"""
                            return (
                                "\n[prompt]Query[/] "
                                "([command]:n[/] new session, [command]:d[/] change domain, [command]:q[/] quit)"
                            )

                        message = Prompt.ask(get_prompt_text()).strip()

                        if not message:
                            continue

                        if message == ":q":
                            console.print("[success]Goodbye![/]")
                            return

                        if message == ":d":
                            new_domain = change_domain(console)
                            if new_domain is None:
                                return
                            current_domain = new_domain
                            break

                        if message == ":n":
                            console.print("[info]Starting new session...[/]")
                            interface_agent, message_history = init_session(
                                current_domain
                            )
                            continue

                        with console.status("[info]Processing query...[/]"):
                            response, message_history = interface_agent.respond(
                                message, message_history
                            )

                        # Try to parse response as markdown for better formatting
                        try:
                            md = Markdown(response.content)
                            console.print("\n[bold]Response:[/]")
                            console.print(md)
                        except Exception as e:
                            console.print(
                                f"\n[error]Error parsing response:[/] {str(e)}"
                            )
                            console.print("\n[bold]Response:[/]", response.content)

                    except KeyboardInterrupt:
                        console.print("\n[warning]Exiting...[/]")
                        return
                    except Exception as e:
                        console.print(f"\n[error]Error processing message:[/] {str(e)}")

            except Exception as e:
                console.print(
                    f"\n[error]Error initializing domain '{current_domain}':[/] {str(e)}"
                )
                new_domain = change_domain(console)
                if new_domain is None:
                    return
                current_domain = new_domain

    except KeyboardInterrupt:
        console.print("\n[success]Goodbye![/]")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        Console().print("\n[success]Goodbye![/]")
