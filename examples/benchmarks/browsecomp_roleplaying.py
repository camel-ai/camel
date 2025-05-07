from camel.agents.chat_agent import ChatAgent
from camel.benchmarks.browsecomp import BrowseCompBenchmark
from camel.models.model_factory import ModelFactory
from camel.societies.role_playing import RolePlaying
from camel.types.enums import ModelPlatformType, ModelType, TaskType


if __name__ == '__main__':
    model_config = {
        "model_platform": ModelPlatformType.DEFAULT,
        "model_type": ModelType.DEFAULT,
    }

    model = ModelFactory.create(**model_config)
    summarize_agent = ChatAgent('You are a helpful assistant.', model=model)

    # Create a RolePlaying session with appropriate roles for web research
    role_play_session = RolePlaying(
        assistant_role_name="assistant",
        assistant_agent_kwargs=dict(model=model),
        user_role_name="user",
        user_agent_kwargs=dict(model=model),
        task_prompt="Analyze web content and extract accurate information",
        with_task_specify=False,
        task_type=TaskType.AI_SOCIETY,
    )

    benchmark = BrowseCompBenchmark(
        "report_role_playing.html", num_examples=2, processes=2
    )

    benchmark.run(
        pipeline_template=role_play_session,
        roleplaying_summarizer=summarize_agent,
    )

    # Create a grader agent for validation
    grader_agent = ChatAgent(
        "You are a helpful assistant.",
        model=ModelFactory.create(**model_config),
    )

    # Validate the results
    benchmark.validate(grader=grader_agent)
