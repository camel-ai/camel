from camel.agents.chat_agent import ChatAgent
from camel.benchmarks.browsecomp import BrowseCompBenchmark, decrypt
from camel.models.model_factory import ModelFactory
from camel.types.enums import ModelPlatformType, ModelType


def process_each_row(row):
    """
    Process a single example row from the benchmark dataset.

    This function decrypts the problem and answer, creates a model and agent,
    and gets a response from the agent for the problem. It's designed to be
    used with parallel processing in the benchmark's run method.

    Args:
        row (dict): A row from the dataset containing
        encrypted problem and answer

    Returns:
        dict: A dictionary containing the decrypted problem, answer,
        and model response
    """
    # Decrypt the problem and answer using the canary as the password
    # DO NOT MODIFY THIS PART, IT'S A GEMERAL STEP OF BROWNSECOMP BENCHMARK
    problem = decrypt(row.get("problem", ""), row.get("canary", ""))
    answer = decrypt(row.get("answer", ""), row.get("canary", ""))

    # Model configuration for the LLM
    # define the agent you would like to run benchmark on.
    model_config = {
        "model_platform": ModelPlatformType.OPENAI,
        "model_type": ModelType.O1_MINI,
    }

    # Create model for the main process
    model = ModelFactory.create(**model_config)

    # TODO: Browser toolkit is not supported for multiprocessing right now
    # web_toolkit = BrowserToolkit(
    #     headless=False,
    #     web_agent_model=model,
    #     planning_agent_model=model,
    #     channel="chromium",
    # )

    # Create agent for the main process
    agent = ChatAgent(
        system_message="You are a helpful assistant.",
        model=model,
        # tools=[*web_toolkit.get_tools()],
    )

    # Add prompt if necessary
    # DO NOT CHANGE THE RESPONSE FORMAT, IT'S REQUIRED IN THE BENCHMARK
    # CHANGING IT WILL IMPACT FOLLOWUP EVALUATION
    input_message = f"""
{problem}
navigate to related website to find the answer.
            
Your response should be in the following format:
Explanation:{{your explanation for your final answer}}
Exact Answer: {{your succinct, final answer}}
Confidence: {{your confidence score between 0% and 100% for your answer}}
            """.strip()
    response_text = agent.step(input_message)

    return {
        "problem": problem,
        "answer": answer,
        "response": response_text.msgs[0].content,
    }


# Will need to place the benchmark run under
if __name__ == '__main__':
    # Create a benchmark instance with output file "report.html"
    # it samples 2 examples and uses 2 parallel processes for efficiency
    # set num_example=None in case of running full benchmark.
    benchmark = BrowseCompBenchmark("report.html", num_examples=2, processes=2)

    # Run the benchmark using the process_each_row function
    # This will process each example in parallel using separate agents
    # you will need to define your own process_each_row_f,
    # process_each_row is an example for reference.
    benchmark.run(process_each_row_f=process_each_row)

    # Configure the model for validation
    # This model will be used to evaluate the correctness of responses
    model_config = {
        "model_platform": ModelPlatformType.OPENAI,
        "model_type": ModelType.O1_MINI,
    }

    # Validate the results using the configured model
    # This will generate a report.html file with the evaluation results
    # The output AGGRECATION METRICS are rates:
    # {'is_correct': 0.0, 'is_incorrect': 1.0} means is_incorrect=100%
    benchmark.validate(model_config=model_config)
