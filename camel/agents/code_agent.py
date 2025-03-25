import re
import ast
import textwrap
from typing import List, Optional, Type, Union, Callable

from camel.agents.chat_agent import ChatAgent, ChatAgentResponse
from camel.messages import BaseMessage
from pydantic import BaseModel
from camel.toolkits import FunctionTool
from camel.types import OpenAIBackendRole
import logging

from rich.text import Text
from rich.console import Group
logger = logging.getLogger(__name__)

SYSTEM_MESSAGE = """
You are an expert assistant who can solve any task using code blobs. You will be given a task to solve as best you can.
To do so, you have been given access to a list of tools: these tools are basically Python functions which you can call with code.
To solve the task, you must plan forward to proceed in a series of steps, in a cycle of 'Thought:', 'Code:', and 'Observation:' sequences.

At each step, in the 'Thought:' sequence, you should first explain your reasoning towards solving the task and the tools that you want to use.
Then in the 'Code:' sequence, you should write the code in simple Python. The code sequence must end with '<end_code>' sequence.
During each intermediate step, you can use 'print()' to save whatever important information you will then need.
These print outputs will then appear in the 'Observation:' field, which will be available as input for the next step.
In the end you have to return a final answer using the `final_answer` tool.

Here are a few examples using notional tools:
---
Task: "Generate an image of the oldest person in this document."

Thought: I will proceed step by step and use the following tools: `document_qa` to find the oldest person in the document, then `image_generator` to generate an image according to the answer.
Code:
```py
answer = document_qa(document=document, question="Who is the oldest person mentioned?")
print(answer)
```<end_code>
Observation: "The oldest person in the document is John Doe, a 55 year old lumberjack living in Newfoundland."

Thought: I will now generate an image showcasing the oldest person.
Code:
```py
image = image_generator("A portrait of John Doe, a 55-year-old man living in Canada.")
final_answer(image)
```<end_code>

---
Task: "What is the result of the following operation: 5 + 3 + 1294.678?"

Thought: I will use python code to compute the result of the operation and then return the final answer using the `final_answer` tool
Code:
```py
result = 5 + 3 + 1294.678
final_answer(result)
```<end_code>

---
Task:
"Answer the question in the variable `question` about the image stored in the variable `image`. The question is in French.
You have been provided with these additional arguments, that you can access using the keys as variables in your python code:
['question': 'Quel est l'animal sur l'image?', 'image': 'path/to/image.jpg']"

Thought: I will use the following tools: `translator` to translate the question into English and then `image_qa` to answer the question on the input image.
Code:
```py
translated_question = translator(question=question, src_lang="French", tgt_lang="English")
print(f"The translated question is [translated_question].")
answer = image_qa(image=image, question=translated_question)
final_answer(f"The answer is [answer]")
```<end_code>

---
Task:
In a 1979 interview, Stanislaus Ulam discusses with Martin Sherwin about other great physicists of his time, including Oppenheimer.
What does he say was the consequence of Einstein learning too much math on his creativity, in one word?

Thought: I need to find and read the 1979 interview of Stanislaus Ulam with Martin Sherwin.
Code:
```py
pages = search(query="1979 interview Stanislaus Ulam Martin Sherwin physicists Einstein")
print(pages)
```<end_code>
Observation:
No result found for query "1979 interview Stanislaus Ulam Martin Sherwin physicists Einstein".

Thought: The query was maybe too restrictive and did not find any results. Let's try again with a broader query.
Code:
```py
pages = search(query="1979 interview Stanislaus Ulam")
print(pages)
```<end_code>
Observation:
Found 6 pages:
[Stanislaus Ulam 1979 interview](https://ahf.nuclearmuseum.org/voices/oral-histories/stanislaus-ulams-interview-1979/)

[Ulam discusses Manhattan Project](https://ahf.nuclearmuseum.org/manhattan-project/ulam-manhattan-project/)

(truncated)

Thought: I will read the first 2 pages to know more.
Code:
```py
for url in ["https://ahf.nuclearmuseum.org/voices/oral-histories/stanislaus-ulams-interview-1979/", "https://ahf.nuclearmuseum.org/manhattan-project/ulam-manhattan-project/"]:
    whole_page = visit_webpage(url)
    print(whole_page)
    print("\n" + "="*80 + "\n")  # Print separator between pages
```<end_code>
Observation:
Manhattan Project Locations:
Los Alamos, NM
Stanislaus Ulam was a Polish-American mathematician. He worked on the Manhattan Project at Los Alamos and later helped design the hydrogen bomb. In this interview, he discusses his work at
(truncated)

Thought: I now have the final answer: from the webpages visited, Stanislaus Ulam says of Einstein: "He learned too much mathematics and sort of diminished, it seems to me personally, it seems to me his purely physics creativity." Let's answer in one word.
Code:
```py
final_answer("diminished")
```<end_code>

---
Task: "Which city has the highest population: Guangzhou or Shanghai?"

Thought: I need to get the populations for both cities and compare them: I will use the tool `search` to get the population of both cities.
Code:
```py
for city in ["Guangzhou", "Shanghai"]:
    print(f"Population [city]:", search(f"[city] population")
```<end_code>
Observation:
Population Guangzhou: ['Guangzhou has a population of 15 million inhabitants as of 2021.']
Population Shanghai: '26 million (2019)'

Thought: Now I know that Shanghai has the highest population.
Code:
```py
final_answer("Shanghai")
```<end_code>

---
Task: "What is the current age of the pope, raised to the power 0.36?"

Thought: I will use the tool `wiki` to get the age of the pope, and confirm that with a web search.
Code:
```py
pope_age_wiki = wiki(query="current pope age")
print("Pope age as per wikipedia:", pope_age_wiki)
pope_age_search = web_search(query="current pope age")
print("Pope age as per google search:", pope_age_search)
```<end_code>
Observation:
Pope age: "The pope Francis is currently 88 years old."

Thought: I know that the pope is 88 years old. Let's compute the result using python code.
Code:
```py
pope_current_age = 88 ** 0.36
final_answer(pope_current_age)
```<end_code>

Above example were using notional tools that might not exist for you. On top of performing computations in the Python code snippets that you create, you only have access to these tools:

{tools}

- final_answer: Provides a final answer to the given problem.
    Takes inputs: ['answer': ['type': 'any', 'description': 'The final answer to the problem']]
    Returns an output of type: any

Here are the rules you should always follow to solve your task:
1. Always provide a 'Thought:' sequence, and a 'Code:\n```py' sequence ending with '```<end_code>' sequence, else you will fail.
2. Use only variables that you have defined!
3. Always use the right arguments for the tools. DO NOT pass the arguments as a dict as in 'answer = wiki(['query': "What is the place where James Bond lives?"])', but use the arguments directly as in 'answer = wiki(query="What is the place where James Bond lives?")'.
4. Take care to not chain too many sequential tool calls in the same code block, especially when the output format is unpredictable. For instance, a call to search has an unpredictable return format, so do not have another tool call that depends on its output in the same block: rather output results with print() to use them in the next block.
5. Call a tool only when needed, and never re-do a tool call that you previously did with the exact same parameters.
6. Don't name any new variable with the same name as a tool: for instance don't name a variable 'final_answer'.
7. Never create any notional variables in our code, as having these in your logs will derail you from the true variables.
8. You can use imports in your code, but only from the following list of modules: ['collections', 'datetime', 'itertools', 'math', 'queue', 'random', 're', 'stat', 'statistics', 'time', 'unicodedata']
9. The state persists between code executions: so if in one step you've created variables or imported modules, these will all persist.
10. Don't give up! You're in charge of solving the task, not providing directions to solve it.

Now Begin! If you solve the task correctly, you will receive a reward of $1,000,000.
"""
def _parse_code_blobs(text: str) -> str:
    """Extract code blocks from the LLM's output.

    If a valid code block is passed, it returns it directly.

    Args:
        text (`str`): LLM's output text to parse.

    Returns:
        `str`: Extracted code block.

    Raises:
        ValueError: If no valid code block is found in the text.
    """
    pattern = r"```(?:py|python)?\n(.*?)\n```"
    matches = re.findall(pattern, text, re.DOTALL)
    if matches:
        return "\n\n".join(match.strip() for match in matches)
    # Maybe the LLM outputted a code blob directly
    try:
        ast.parse(text)
        return text
    except SyntaxError:
        pass

    if "final" in text and "answer" in text:
        raise ValueError(
            textwrap.dedent(
                f"""
                Your code snippet is invalid, because the regex pattern {pattern} was not found in it.
                Here is your code snippet:
                {text}
                It seems like you're trying to return the final answer, you can do it as follows:
                Code:
                ```py
                final_answer("YOUR FINAL ANSWER HERE")
                ```
                """
            ).strip()
        )
    raise ValueError(
        textwrap.dedent(
            f"""
            Your code snippet is invalid, because the regex pattern {pattern} was not found in it.
            Here is your code snippet:
            {text}
            Make sure to include code with the correct pattern, for instance:
            Thoughts: Your thoughts
            Code:
            ```py
            # Your python code here
            ```
            """
        ).strip()
    )


def _fix_final_answer_code(code: str) -> str:
    """
    Sometimes an LLM can try to assign a variable to final_answer, which would break the final_answer() tool.
    This function fixes this behaviour by replacing variable assignments to final_answer with final_answer_variable,
    while preserving function calls to final_answer().
    """
    # First, find if there's a direct assignment to final_answer
    # Use word boundary and negative lookbehind to ensure it's not an object attribute
    assignment_pattern = r"(?<!\.)(?<!\w)\bfinal_answer\s*="
    if "final_answer(" not in code or not re.search(assignment_pattern, code):
        # If final_answer tool is not called in this blob, then doing the replacement is hazardous
        # because it could affect the model's memory for next steps.
        # Let's not modify the code and leave the subsequent assignment error happen.
        return code

    # Pattern for replacing variable assignments
    # Looks for 'final_answer' followed by '=' with optional whitespace
    # Negative lookbehind ensures we don't match object attributes
    assignment_regex = r"(?<!\.)(?<!\w)(\bfinal_answer)(\s*=)"
    code = re.sub(assignment_regex, r"final_answer_variable\2", code)

    # Pattern for replacing variable usage but not function calls
    # Negative lookahead (?!\s*\() ensures we don't match function calls
    # Negative lookbehind (?<!\.|\w) ensures we don't match object methods or other variables
    variable_regex = r"(?<!\.)(?<!\w)(\bfinal_answer\b)(?!\s*\()"
    code = re.sub(variable_regex, "final_answer_variable", code)
    return code


class CodeExecutionEnvironment:
    """Environment for executing Python code with tools."""
    
    def __init__(self, agent):
        self.agent = agent
        self.globals = {}
        self.locals = {}
        self._print_outputs = ""
        self._final_answer = None
        self._is_final_answer = False
        self._setup_environment()
    
    def _setup_environment(self):
        """Set up the execution environment with tools."""
        for tool_name, tool in self.agent.tool_dict.items():
            self.globals[tool_name] = tool.__call__
        
        def final_answer(answer):
            self._final_answer = answer
            self._is_final_answer = True
            return answer
        
        self.globals["final_answer"] = final_answer
        
        def custom_print(*args, **kwargs):
            output = " ".join(str(arg) for arg in args)
            end = kwargs.get("end", "\n")
            self._print_outputs += output + end
            return None
        
        self.globals["print"] = custom_print
    
    def execute(self, code):
        """
        Execute the given code in the environment.
        
        Returns:
            tuple: (output, logs, is_final_answer)
        """
        self._print_outputs = ""
        self._is_final_answer = False
        
        try:
            # Execute the code
            exec(code, self.globals, self.locals)
            
            # Return the final result or None
            output = self._final_answer if self._is_final_answer else None
            return output, self._print_outputs, self._is_final_answer
        except Exception as e:
            # Append the error to print outputs
            self._print_outputs += f"\nError: {str(e)}"
            raise e


class CodeAgent(ChatAgent):
    r"""
    An agent that interprets and executes Python code from LLM outputs.
    
    This agent extends ChatAgent by adding capabilities to:
    1. Instruct the LLM to output Python code
    2. Parse the code blocks from LLM output
    3. Execute the code in a controlled environment
    4. Process the results as observations
    
    Args:
        system_message (BaseMessage or str, optional): System message for the agent
        tools: List of tools to be used by the agent
        **kwargs: Additional arguments to pass to ChatAgent
    """
    
    def __init__(
        self,
        tools: Optional[List[Union[FunctionTool, Callable]]] = None,
        **kwargs
    ) -> None:

        super().__init__(tools=tools, **kwargs)

        tool_schemas = self._get_full_tool_schemas()
        tools_str = ""
        for item in tool_schemas:
            tools_str += str(item) + "\n"
        self.default_system_message = SYSTEM_MESSAGE.format(tools=tools_str)
        
        self._system_message = BaseMessage.make_assistant_message(
            role_name="Assistant",
            content=self.default_system_message
        )
        
        self.code_executor = CodeExecutionEnvironment(self)
        self.single_iteration = True
        self.update_memory(self.system_message, OpenAIBackendRole.SYSTEM)

    def step(
        self,
        input_message: Union[BaseMessage, str],
        response_format: Optional[Type[BaseModel]] = None,
    ) -> ChatAgentResponse:
        """
        Execute a step with code parsing and execution.
        
        Args:
            input_message: The input message to process
            response_format: The response format to use
        Returns:
            ChatAgentResponse: The response from the code execution
        """

        if isinstance(input_message, str):
            input_message = BaseMessage.make_user_message(
                role_name="User", content=input_message
            )

        # Add user input to memory
        self.update_memory(input_message, OpenAIBackendRole.USER)

        while True:
            try:
                openai_messages, num_tokens = self.memory.get_context()
            except RuntimeError as e:
                return self._step_token_exceed(
                    e.args[1],  termination_reason = "max_tokens_exceeded"
                )
            # Get response from model backend
            response = self._get_model_response(
                openai_messages,
                num_tokens,
                response_format,
            )

            if self.single_iteration:
                break

        logger.info(
            f"Output message of the LLM: {response.output_messages[0].content}"
        )
        print(response.output_messages[0].content)
        try:
            # Get the text content from the response
            content = response.output_messages[0].content if response.output_messages[0].content else ""
            # Parse code blocks
            code = _parse_code_blobs(content)
            code_action = _fix_final_answer_code(code)
        except Exception as e:
            error_msg = f"Error in code parsing:\n{e}\nMake sure to provide correct code blobs."
            raise error_msg
        
        logger.info(f"Executing parsed code: {code_action}")
        is_final_answer = False
        
        try:
            output, execution_logs, is_final_answer = self.code_executor.execute(code_action)
            print(f"output: {output}, execution_logs: {execution_logs}, is_final_answer: {is_final_answer}")
            execution_outputs_console = []
            if len(execution_logs) > 0:
                execution_outputs_console += [
                    Text("Execution logs:", style="bold"),
                    Text(execution_logs),
                ]
            observation = "Execution logs:\n" + execution_logs
        except Exception as e:
            if hasattr(self.code_executor, "state") and "_print_outputs" in self.code_executor.state:
                execution_logs = str(self.code_executor.state["_print_outputs"])
                if len(execution_logs) > 0:
                    execution_outputs_console = [
                        Text("Execution logs:", style="bold"),
                        Text(execution_logs),
                    ]

                    self.update_memory(BaseMessage.make_assistant_message(
                        role_name="Assistant",
                        content="There are some execution logs:\n" + execution_logs
                    ), OpenAIBackendRole.ASSISTANT)
                    logger.info(Group(*execution_outputs_console))
            error_msg = str(e)
            if "Import of " in error_msg and " is not allowed" in error_msg:
                logger.info(
                    "[bold red]Warning to user: Code execution failed due to an unauthorized import - Consider passing said import under `additional_authorized_imports` when initializing your CodeAgent."
                )
            raise error_msg
        
        observation += "Last output from code snippet:\n" + str(output)
        
        self.update_memory(BaseMessage.make_assistant_message(
            role_name="Assistant",
            content=observation
        ),
        OpenAIBackendRole.ASSISTANT)

        execution_outputs_console += [
            Text(
                f"{('Out - Final answer' if is_final_answer else 'Out')}: {output}",
                style=(f"bold #d4b702" if is_final_answer else ""),
            ),
        ]
        logger.info(Group(*execution_outputs_console))
        
        self.update_memory(BaseMessage.make_assistant_message(
            role_name="Assistant",
            content="here is the execution output:\n" + output if output else ""
        ), OpenAIBackendRole.ASSISTANT)

        self._system_message = BaseMessage.make_assistant_message(
            role_name="Assistant",
            content="you are a helpful assistant"
        )
        if is_final_answer:
            response = super().step('Please give a final summary based on the above results')
        else:
            response = None

        self._system_message = BaseMessage.make_assistant_message(
            role_name="Assistant",
            content=self.default_system_message
        )

        return response
        
