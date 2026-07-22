.. _paper_to_code_agent_cookbook:

##############################
Using the PaperToCodeAgent
##############################

The `PaperToCodeAgent` is a specialized agent designed to convert research papers into executable code. It takes a research paper (currently in JSON or LaTeX format) as input and follows a multi-phase process to generate a project structure with code aimed at reproducing the paper's methodology and experiments.

Overview
========

The agent operates in several distinct phases:

1.  **Planning**: Analyzes the paper to create a high-level plan, including an overview, system design (file list, data structures, call flows), and a task list with dependencies.
2.  **Analyzing**: Takes the output from the planning phase and conducts a detailed logic analysis for each file to be implemented.
3.  **Coding**: Generates the actual code for each file based on the paper, plans, and analysis.
4.  **Done**: Indicates the process is complete.

Prerequisites
=============

Before running the `PaperToCodeAgent`, ensure you have the necessary API keys set up as environment variables. For example, if using OpenAI models (the default), set your `OPENAI_API_KEY`.

.. code-block:: bash

   export OPENAI_API_KEY="your_openai_api_key_here"

If you are using other models like Anthropic's Claude or Google's Gemini, set their respective API keys (e.g., `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`).

Basic Usage: An Example
=======================

We provide an example script that demonstrates how to set up and run the `PaperToCodeAgent`. You can find this script at `examples/agents/create_paper_to_code_agent.py`.

Let's walk through the key parts of this example.

1. Setting up a Dummy Paper
---------------------------

For demonstration purposes, the example script first creates a simple dummy JSON file representing a research paper:

.. literalinclude:: ../../../examples/agents/create_paper_to_code_agent.py
   :language: python
   :lines: 15-30

This creates a file named `dummy_paper_for_ptc.json` in the `examples/data/` directory.

2. Initializing the Agent
-------------------------

Next, the `PaperToCodeAgent` is initialized. You need to provide:
    - `file_path`: Path to the input paper.
    - `paper_name`: A name for the paper, used to create output directories.
    - `paper_format`: The format of the input paper (e.g., "JSON").
    - `model` (optional): You can specify a particular model backend. If not provided, it defaults to an OpenAI model.

.. literalinclude:: ../../../examples/agents/create_paper_to_code_agent.py
   :language: python
   :lines: 44-49
   :emphasize-lines: 1-6

The agent will create directories `./<paper_name>/output/` and `./<paper_name>/repo/` in the current working directory where the script is executed. The example script includes a cleanup step to remove these directories from previous runs.

3. Running the Agent's Steps
----------------------------

The agent progresses through its phases by calling the `step()` method. The agent manages its internal state.

The first call to `step()` typically initiates the **planning** phase:

.. literalinclude:: ../../../examples/agents/create_paper_to_code_agent.py
   :language: python
   :lines: 55-60

The `step()` method returns a `PaperToCodeAgentResponse` object, which contains:
    - `action_phase`: The phase the agent will execute in the *next* step (e.g., if "planning" was just completed, this might be "analyzing").
    - `content`: The output from the completed phase. For the planning phase, this is typically a list of `ChatAgentResponse` objects (serialized as dictionaries) representing different sub-outputs of planning (overview, design, tasks, config).
    - `terminated`: A boolean indicating if the agent has reached its "done" state.

The example script shows how to print the response from the initial planning step:

.. literalinclude:: ../../../examples/agents/create_paper_to_code_agent.py
   :language: python
   :lines: 62-81

4. Iterating Through Phases
---------------------------

To complete the entire paper-to-code process, you would continue to call `agent.step()` in a loop until `response.terminated` is true. The agent internally transitions from planning to analyzing, and then to coding.

The example script includes a commented-out section demonstrating this loop:

.. literalinclude:: ../../../examples/agents/create_paper_to_code_agent.py
   :language: python
   :lines: 90-103

Expected Output
===============

As the `PaperToCodeAgent` runs, it generates files in two main subdirectories under the `<paper_name>` directory (e.g., `MyDummyPaper/`):

-   **`<paper_name>/output/`**: Contains intermediate files generated during the planning and analyzing phases.
    -   `planning_overview.txt`: Text overview of the plan.
    -   `planning_design.json`: JSON file with system design details.
    -   `planning_tasks.json`: JSON file with task breakdown and dependencies.
    -   `planning_config.yaml`: YAML configuration extracted or generated.
    -   `analyzing_logic_<filename>.md`: Markdown files containing detailed logic analysis for each code file.

-   **`<paper_name>/repo/`**: Contains the final generated code files, organized according to the plan.

Running the Example
===================

To run the example:

1.  Ensure your API keys are set.
2.  Navigate to the `examples/agents/` directory or run it using its full path:

.. code-block:: bash

   python /path/to/your/camel/examples/agents/create_paper_to_code_agent.py

After execution, inspect the `MyDummyPaper/` directory (or whatever `paper_name` you used) to see the generated outputs.

Further Customization
=====================

-   **Models**: You can pass different model backends (e.g., `AnthropicModel`, `GoogleModel`) to the `PaperToCodeAgent` constructor.
-   **Input Paper**: While the example uses a JSON file, the agent is designed to also support LaTeX in the future (check agent implementation for current status).
-   **Prompts**: The agent uses internal prompts for each phase. Advanced users could potentially customize these by modifying the agent's source code, though this is not typically required.

This cookbook provides a starting point for using the `PaperToCodeAgent`. For more detailed API information, refer to the agent's source code documentation (docstrings in `camel/agents/paper_to_code_agent.py`) and the generated API documentation after building the project's docs.
