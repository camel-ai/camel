import textwrap
from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.societies.workforce import Workforce
from camel.tasks import Task
from camel.toolkits import FunctionTool, SearchToolkit
from camel.types import ModelPlatformType, ModelType


def make_judge(persona: str, example_feedback: str,
               criteria: str) -> ChatAgent:
    content = textwrap.dedent(
        f"""\
        You are a judge in a hackathon.
        Persona: {persona}
        Example feedback: {example_feedback}
        Criteria:
        {criteria}
        Give a score like 3/4, 4/4, etc. Be true to your persona.
        """
    )
    return ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Hackathon Judge", content=content
        ),
        model=ModelFactory.create(ModelPlatformType.DEFAULT,
                                  ModelType.DEFAULT),
    )


def make_head_judge() -> ChatAgent:
    content = textwrap.dedent(
        """\
        You are the head judge in a hackathon.
        Your task is to read the reviews and scores from other judges,
        and summarize them into one unified final evaluation.
        You should include each judge's score, identity, and feedback,
        and then offer a final paragraph summary for the project.
        """
    )
    return ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Head Judge", content=content
        ),
        model=ModelFactory.create(ModelPlatformType.DEFAULT,
                                  ModelType.DEFAULT),
    )


def main():
    # Judges
    vc_agent = make_judge(
        "A buzzword-loving VC looking for unicorn potential.",
        "Absolutely disruptive! Perfect for the FinTech ecosystem!",
        "### Market Potential (1-4):\n- 4: Unicorn-ready\n- 1: No market"
    )

    eng_agent = make_judge(
        "A perfectionist systems engineer who hates inefficiencies.",
        "Architecture is unstable and barely performs under load.",
        "### Technical Quality (1-4):\n- 4: Flawless\n- 1: Broken"
    )

    contributor_agent = make_judge(
        "A CAMEL contributor who loves to see CAMEL used creatively.",
        "Love how CAMEL-AI is integrated! So much potential!",
        "### CAMEL Integration (1-4):\n- 4: Advanced use\n- 1: Basic use"
    )

    researcher_agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Researcher",
            content="You search the web to provide supporting context.",
        ),
        model=ModelFactory.create(ModelPlatformType.DEFAULT,
                                  ModelType.DEFAULT),
        tools=[
            FunctionTool(SearchToolkit().search_google),
        ],
    )

    head_judge = make_head_judge()

    # Create workforce
    workforce = Workforce("Hackathon Judging Committee")
    workforce.add_single_agent_worker("VC Veronica", vc_agent)
    workforce.add_single_agent_worker("Engineer Ethan", eng_agent)
    workforce.add_single_agent_worker("Contributor Clara", contributor_agent)
    workforce.add_single_agent_worker("Researcher Rachel", researcher_agent)
    workforce.add_single_agent_worker("Head Judge Henry", head_judge)

    # Build task sequence
    task_list = [
        Task(
            id="research",
            content=(
                "Do a brief research on the hackathon project. Summarize the "
                "core idea, "
                "technology used, innovation, and potential impact."
            )
        ),
        Task(
            id="judge_A",
            content=(
                "As Judge Alice, review the project based on the research "
                "summary. "
                "Provide your opinion and give a score from 1 to 10. Be "
                "specific about "
                "what you liked or disliked."
            )
        ),
        Task(
            id="judge_B",
            content=(
                "As Judge Bob, evaluate the project using your own criteria. "
                "Based on the research summary, give a thoughtful critique "
                "and assign "
                "a score from 1 to 10."
            )
        )]

    results = workforce.process_task_sequence(task_list)

    for t in results:
        print(f"Task {t.id} result:\n{t.result}\n")

    print("=== Shared Context ===")
    for k, v in workforce.shared_context.items():
        print(f"{k}: {v['result']}\n")


if __name__ == "__main__":
    main()
