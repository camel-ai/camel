import os
import shutil  # For potential cleanup

from camel.agents import PaperToCodeAgent

# --- Setup Dummy Paper ---
# Define the directory for example data and create it if it doesn't exist
# Assumes this script is in 'examples/agents/'
current_script_dir = os.path.dirname(os.path.abspath(__file__))
# Path to 'examples/data/'
data_dir = os.path.join(os.path.dirname(current_script_dir), "data")
os.makedirs(data_dir, exist_ok=True)

# Define the dummy paper file path and content
dummy_paper_file = os.path.join(data_dir, "dummy_paper_for_ptc.json")

# ruff: noqa: E501
dummy_paper_content = """
{
  "title": "A Simple Method for Test Generation",
  "abstract": "This paper introduces a novel, yet simple, method for generating test cases automatically.",
  "sections": [
    {
      "heading": "Introduction",
      "text": "Automatic test generation is crucial for software quality."
    },
    {
      "heading": "Methodology",
      "text": "Our method involves parsing the abstract and creating a plan."
    }
  ]
}
"""

# Create the dummy paper file
with open(dummy_paper_file, "w", encoding="utf-8") as f:
    f.write(dummy_paper_content)

print(f"Dummy paper created at: {dummy_paper_file}")

# --- Initialize PaperToCodeAgent ---
# IMPORTANT: Ensure your OPENAI_API_KEY environment variable is set for the default OpenAI model.
# If you use other models, ensure their respective API keys are set (e.g., ANTHROPIC_API_KEY).
#
# The agent will create output directories: './MyDummyPaper/output/' and './MyDummyPaper/repo/'
# in the current working directory where this script is run.

paper_name_for_outputs = "MyDummyPaper"

# Clean up previous run directories if they exist to avoid conflicts
if os.path.exists(paper_name_for_outputs):
    print(f"Removing existing output directory: ./{paper_name_for_outputs}")
    shutil.rmtree(paper_name_for_outputs)

try:
    # You can specify a model, e.g., model=OpenAIModel(ModelType.GPT_4O_MINI)
    # If no model is specified, it defaults to OpenAIModel().
    agent = PaperToCodeAgent(
        file_path=dummy_paper_file,
        paper_name=paper_name_for_outputs,  # Used for creating output folders
        paper_format="JSON",
        # model=OpenAIModel(model_type=ModelType.GPT_4O_MINI) # Example of specifying a model
    )
    print(f"PaperToCodeAgent initialized for paper: {paper_name_for_outputs}")
    print(
        f"Output will be generated in ./{paper_name_for_outputs}/ relative to the script's CWD."
    )

    # --- First step: Planning ---
    # The agent starts in the 'planning' phase by default.
    # The input_message can provide additional context or instructions for this phase.
    initial_user_message = "Please generate a comprehensive plan to reproduce the methodology described in this paper."

    print(
        f"\nAttempting first step (planning) with message: '{initial_user_message}'"
    )
    # The step method progresses the agent through its internal phases (planning -> analyzing -> coding -> done)
    # It returns a PaperToCodeAgentResponse object.
    response = agent.step(initial_user_message)

    print("\n--- Response from PaperToCodeAgent (Initial Step: Planning) ---")
    print(f"Action Phase Completed by Agent: {response.action_phase}"
         )  # Should be 'analyzing' if planning was successful
    print(f"Is Process Terminated: {response.terminated}")

    if response.content:
        print(f"Number of content items from planning: {len(response.content)}")
        # The content from the planning phase is a list of dictionaries (serialized ChatAgentResponse).
        # Each dictionary corresponds to a sub-step in the planning process.
        for i, chat_response_dict in enumerate(response.content):
            print(
                f"\nContent Item {i+1} (Represents a planning sub-step output):"
            )
            if isinstance(chat_response_dict,
                          dict) and 'msgs' in chat_response_dict:
                for msg_dict in chat_response_dict['msgs']:
                    if 'content' in msg_dict and msg_dict.get(
                            'role') == 'assistant':
                        print(f"  LLM Output for sub-step {i+1}:")
                        print("  ------------------------------------")
                        # The actual plan/design/tasks from the LLM
                        print(msg_dict['content'])
                        print("  ------------------------------------")
            else:
                print(f"  Raw content item {i+1}: {chat_response_dict}")
    else:
        print("No content in the response from the planning phase.")

    # --- Subsequent Steps ---
    # To continue to the next phase (e.g., analyzing, then coding),
    # you would call agent.step() again. The agent manages its state internally.
    # The input_message for subsequent steps might often be an empty string or a generic prompt,
    # as the agent primarily uses its internal state and files generated in previous phases.

    # Example of proceeding (run these calls sequentially):
    # current_response = response
    # while not current_response.terminated:
    #     next_phase_to_execute = agent.status # The phase the agent is currently in and will execute next
    #     print(f"\nAttempting next step ({next_phase_to_execute})...")
    #     current_response = agent.step("Continue to the next phase.")
    #     print(f"\n--- Response from PaperToCodeAgent ({next_phase_to_execute} Phase) ---")
    #     print(f"Action Phase Completed by Agent: {current_response.action_phase}")
    #     print(f"Is Process Terminated: {current_response.terminated}")
    #     if current_response.content:
    #         # Process and print content similar to above, adapting to expected structure for each phase
    #         print(f"Content from {next_phase_to_execute} phase received.")
    #     else:
    #         print(f"No content in the response from the {next_phase_to_execute} phase.")

    print(
        "\nExample finished. Check the './MyDummyPaper/' directory for outputs."
    )

except Exception as e:
    print(f"\nAn error occurred: {e}")
    print(
        "Please ensure your API keys (e.g., OPENAI_API_KEY) are set and valid.")
    print(
        "If using a specific model, ensure it's available and configured correctly."
    )

finally:
    # Optional: Clean up the dummy paper.
    # The output directories ('MyDummyPaper') are left for inspection.
    if os.path.exists(dummy_paper_file):
        # os.remove(dummy_paper_file) # Uncomment to clean up dummy paper
        # print(f"\nDummy paper {dummy_paper_file} could be removed here.")
        pass
    # To clean up output directories:
    # if os.path.exists(paper_name_for_outputs):
    #     shutil.rmtree(paper_name_for_outputs)
    #     print(f"Output directory ./{paper_name_for_outputs} could be removed here.")
    pass
