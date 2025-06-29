from camel.types import ModelType
from camel.agents import CodeReviewAgent
from camel.models import BaseModelBackend, ModelFactory
from camel.types import (
    ModelPlatformType,
    ModelType,
    OpenAIBackendRole,
    RoleType,
)
import os
from github import Github

def main():
    repo_full_name = "camel-ai/camel"
    pr_number = 2390
    max_context_tokens = 10000

    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type="gpt-4.1-2025-04-14",
        url="https://api.openai.com/v1/",
    )

    agent = CodeReviewAgent(
        model=model,
        github_token=os.getenv("GITHUB_AUTH_TOKEN")
        repo_full_name=repo_full_name,
        max_context_tokens=max_context_tokens,
    )

    response = agent.step(
        input_message="Please review the code changes in this PR.",
        commit_sha=os.getenv("BASE_SHA"),
    )

    for msg in response.msgs:
        print(msg.content)
        print("==================================================")

if __name__ == "__main__":
    main()

"""
max_token_context = 15000
standard_review

--- Chunk #1 ---
Files included: ['camel/agents/__init__.py', 'camel/agents/paper_to_code_agent.py', 'examples/agents/create_paper_to_code_agent.py', 'test/agents/test_paper_to_code_agent.py']
Message preview: You are an AI code reviewer working in **standard review mode**, analyzing all file diffs in a single Pull Request (PR).

Your goal is to provide structured, actionable code review feedback for **each ...

## File: camel/agents/__init__.py

**Overall Impression:**  
The modification appropriately adds `PaperToCodeAgent` to the imports and the `__all__` list. This maintains the code pattern seen in the file, and improves discoverability of the new agent.

- 🔐 **Security:**  
  - No major issues found. Simple import/export changes do not introduce security risks.

- 🎨 **Code Style:**  
  - Code style is clear and consistent with existing structure.

- ⚙️ **Performance:**  
  - No performance implications from import and `__all__` edits.

- 🧩 **Maintainability:**  
  - Good maintainability. Updating the `__all__` and imports means users can reliably import the new agent from the package.

---

## File: camel/agents/paper_to_code_agent.py

**Overall Impression:**
This is a large, well-structured addition introducing the `PaperToCodeAgent`, a powerful agent that converts research papers into executable code through planning, analysis, and coding phases. The implementation is clean and uses Pydantic models for schema enforcement and serialization. Proper folder handling and output management is present.

- 🔐 **Security:**
  - Good:
    - No hardcoded secrets present.
    - Attempts to import AgentOps and only activates tracking if the relevant API key is present.
    - Input file handling is explicit; file paths are built using variables.
  - Watch:
    - The use of `os.makedirs()` and `open()` for arbitrary paths means consumers must ensure safe file paths to avoid directory traversal or overwriting important files. Consider validating or sanitizing `file_path` and `paper_name`.
    - The agent writes/parses YAML and JSON—ensure papers and config inputs are trusted, or add validation if accepting any user-uploaded data.
  - No dangerous subprocess or shell execution is present.

- 🎨 **Code Style:**
  - Good:
    - Docstrings for all classes and main methods are clear and detailed (Google style).
    - Type hints are comprehensive and consistent.
    - Constants are uppercased and well-named.
    - Line continuation and logic wrapping is handled well for long or complex lines.
  - Minor suggestions:
    - Consider more consistent use of f-strings, especially for log statements.
    - The use of `os.makedirs(..., exist_ok=True)` is correct and safe.

- ⚙️ **Performance:**
  - No major issues found. All loops are over reasonable lists or dictionaries.
  - Caching or memoization is not necessary here due to the stateful, stepwise workflow.
  - Reading/writing files is done once per major step. No excessive resource use.

- 🧩 **Maintainability:**
  - Good:
    - Method decomposition is clear (_process, _planning, _extract_config, etc.).
    - Error handling and logging is present and informative, especially for file/JSON failures.
    - Pydantic models are used for schema—this will help with future extensibility.
    - The annotated docstrings and comments throughout help future maintainers.
    - All file output paths are parameterized via instance variables.
    - Constants for prompts reduce duplication.
  - Suggestions:
    - The method `_extract_planning` truncates to `context_lst = context_lst[:3]`, which assumes the exact number/order of steps; document this assumption or make it more robust to structure changes.
    - The transformation of file names to file-system-safe names (`replace("/", "_")`) could be shared in a utility function, especially as it appears in multiple spots.
    - Consider extracting long prompt strings to dedicated `.prompt` or `.md` files if they become hard to maintain inline.
    - If the agent is to become multi-threaded or reusable in parallel, ensure the working/output directories are always isolated between instances.

---

## File: examples/agents/create_paper_to_code_agent.py

**Overall Impression:**
This is a comprehensive example for setting up and using the `PaperToCodeAgent`, including dummy data creation and safe cleanup. It is highly useful for users onboarding the new agent.

- 🔐 **Security:**
  - No major issues found. Dummy data is hardcoded and all file operations are local and well-contained.
  - Paths use `os.path.join` and are confined to known directories.

- 🎨 **Code Style:**
  - Excellent structure and comments explaining usage for new users.
  - Shows good usage of path operations and docstrings in script comments.
  - Code follows PEP8 with good naming and spacing.
  - The script gives users hooks for manual cleanup, which is good style for examples.

- ⚙️ **Performance:**
  - No concerns—creates small files and performs only a few steps.
  - The dummy paper data is small and operations are quick.

- 🧩 **Maintainability:**
  - Very easy to read and adapt for other papers.
  - Inline doc/comments are clear on how to proceed to different phases of agent execution.
  - Nice handling of cleaning up outputs for if/when users want to rerun or reset.

---

## File: test/agents/test_paper_to_code_agent.py

**Overall Impression:**
This is a strong and thorough test suite, exercising both the cleaning function and a full mocked workflow of the agent. It employs good testing strategies and nicely mocks the LLM/model backend to ensure repeatability.

- 🔐 **Security:**
  - No security risks. Test files and paths are managed via pytest's tmp_path fixtures.
  - All file I/O and patching is local and safe.

- 🎨 **Code Style:**
  - Well-formatted pytest functions.
  - Good separation into reusable fixtures and test functions.
  - Mocks are constructed with correct structure for what the agent expects.
  - Descriptive function and variable naming.

- ⚙️ **Performance:**
  - Tests are fast, using small dummy data and avoiding real LLM/network calls thank to `patch`.
  - Efficient use of temp directories prevents pollution of actual disk.

- 🧩 **Maintainability:**
  - Highly maintainable: fixtures can be expanded, and test logic matches the actual agent flow.
  - Good inline docstrings and comments.
  - Proper assertions on both file creation and file content.
  - Easy to add new step mocks if agent workflow changes.

---

**Summary:**
This PR introduces a highly modular and extensible `PaperToCodeAgent` with excellent documentation, schema enforcement, and full example and test coverage. The code adheres to high standards for safety, style, and clarity, and is suitable for productionization and future extension.

**Actionable Suggestions:**
- Consider adding path validation/sanitization for externally provided files and directories as a defense-in-depth step.
- Add a few comments or an assertion in `_extract_planning` to clarify/verify the expected number of plan steps.
- If/when the codebase grows, extracting very long prompts to separate files/modules may aid maintainability.
- Otherwise, no major improvements are required.

**Excellent work overall!**

"""





"""
max_token_context = 15000
standard_review

--- Chunk #1 ---
Files included: ['camel/agents/__init__.py', 'camel/agents/paper_to_code_agent.py']
Message preview: You are an AI code reviewer working in **standard review mode**, analyzing all file diffs in a single Pull Request (PR).

Your goal is to provide structured, actionable code review feedback for **each ...

--- Chunk #2 ---
Files included: ['examples/agents/create_paper_to_code_agent.py', 'test/agents/test_paper_to_code_agent.py']
Message preview: You are an AI code reviewer working in **standard review mode**, analyzing all file diffs in a single Pull Request (PR).

Your goal is to provide structured, actionable code review feedback for **each ...

## File: camel/agents/__init__.py

**Overall impressions:**  
This file has a small and straightforward change: addition of `PaperToCodeAgent` to both the import list and the `__all__` export list.

- 🔐 **Security:**  
  - No major issues found. Simple import/export statement.

- 🎨 **Code Style:**  
  - No major issues found. The naming and style are consistent with the rest of the file.

- ⚙️ **Performance:**  
  - No major issues found. Import/export changes only.

- 🧩 **Maintainability:**  
  - No major issues found. Good practice in adding the new agent to `__all__`.
  - **Suggestion:** If the list of agents keeps growing, consider refactoring to load them dynamically, but for now, the explicit declaration is fine.

---

## File: camel/agents/paper_to_code_agent.py

**Overall impressions:**
This is a large, complex, and well-structured new module introducing an agent to convert research papers to code via multiple phases (planning, design, analysis, coding). The implementation uses detailed prompt engineering, multiple (Pydantic) schema models for structured outputs, clear docstrings, and stepwise processing. The module also includes file I/O, process flow management, and integration with external tracking (AgentOps, camel utils), all done quite consistently.

### 🔐 Security

- **High-level file/network access:**
  - Many file read/write operations are performed (including writing outputs, copying configs, and reading large paper files). These use filenames based on user input (`paper_name`, `file_path`).
    - **Suggestion:** Consider validating `paper_name` and `file_path` to prevent directory traversal or injection attacks, especially if this will ever receive non-trusted user input.
    - Prefer `os.path.join` rather than string concatenation for building file paths.
- **YAML parsing:** The code only writes YAML config, doesn't parse it—no risk here.
- **Third party import pattern:** Good fallback logic for AgentOps, minimal risk — but no input from user is passed to the imports themselves.
- **No secrets or keys are written directly.**

### 🎨 Code Style

- **Naming & Typing:**
  - Consistent use of type annotations and clear variable/method names.
  - Models use Pydantic v2 API correctly.
  - String templates, constants, and prompt templates are named and grouped coherently.
- **Formatting:**
  - Consistent indentation and blank lines.
  - Adequate, well-structured docstrings for class/methods.
- **Imports:**
  - All dependencies used, clean import blocks. Some can be grouped for tidiness but that's optional.
- **Error/Log messages:**
  - Good use of the logger for error and info reporting.
  - Consider using `logger.exception` instead of `logger.error` for exceptions to include traceback.
- **Small nits:**
  - Minor typos: `_PLANING_...` → should be `_PLANNING_...` for consistency (but this is not user-facing code).

### ⚙️ Performance

- **Loops and File Operations:**
  - No computationally heavy loops; main performance bottleneck may be repeated file I/O and intermediate file generation.
  - Cleaning the paper JSON (`_remove_spans`) is recursive, but reasonable as long as input papers are not extremely nested or huge.
- **Memory Usage:**
  - Large papers could result in high memory usage when loading the whole paper into RAM. Consider supporting streaming/line-by-line read for large documents in future work.
- **Robustness:**
  - There is some redundancy in reading/writing config/artifacts multiple times, but for batch processing this is acceptable.
- **Prompt rendering efficiency:**
  - Multi-stage prompt approach is clear and modular (each operates sequentially, so no wasted work).

### 🧩 Maintainability

- **Modularity & Structure:**
  - The multi-phase breakdown (planning/analysis/coding) is clean and separated.
  - Helper methods (`_planning`, `_analyzing`, etc.) encourage modular maintenance.
- **Docstrings & Comments:**
  - Excellent class and method docstrings make the workflow very clear.
- **Schema Definitions:**
  - Pydantic models are thoughtfully defined, validated, and documented with examples.
  - Good use of field aliases for schema keys matching LLM prompt conventions.
- **Extensibility:**
  - Easy to add new phases or enhance prompts/models.
  - Good logging to help debugging.
- **Potential refactoring/nits:**
  - There's some coupling between phases via shell file paths and keys; encapsulating intermediate data loading with a utility class for each phase may improve maintainability if features grow.
  - Several hardcoded strings/file names (e.g., `"planning_config.yaml"`, output dirs) — consider module-level constants for these.
  - Consider defensive checks when parsing JSON and reading expected files for more robust error messages/user feedback.
- **Config Saving:**
  - The `_extract_config` method assumes at least four items in 'responses'; a safer access pattern with clearer error/log messages would be better.
- **General Praise:**
  - Well-thought-out process orchestration and extensive structure. Prompting is clear and the process is reproducible.
  - The design accommodates both broad and detailed codebase generation, which is powerful and flexible.

---

### Summary

- **Security:** Only path sanitization is recommended if user input is not trusted.
- **Style:** Very clean, minor typo ("PLANING" vs. "PLANNING").
- **Performance:** Reasonable for stated use but keep an eye on file size/memory scaling.
- **Maintainability:** Well-structured and commented; as the code grows, encapsulating some workflow patterns and path management may help.  

**Overall, this is an impressive and well-structured addition. Great work!**
==================================================
## File: camel/agents/__init__.py

- **Overall impression:**
  The change is minimal—just an import and entry in `__all__`. It’s consistent with the file’s style.

- 🔐 **Security:**
  - No major issues found.

- 🎨 **Code Style:**
  - Naming, indentation, and import placement are correct.
  - Be aware that `__all__` only has meaning if modules are being imported via `from ... import *`, which is rare, but this is consistent with the rest of the file.

- ⚙️ **Performance:**
  - No major issues found.

- 🧩 **Maintainability:**
  - No major issues found. It follows established export patterns.

---

## File: camel/agents/paper_to_code_agent.py

- **Overall impression:**
  A large, sophisticated agent implementation with multi-phase workflow (planning, analysis, coding), heavy use of Pydantic for structured outputs, robust docstrings, modular helpers, logging, and file I/O. Architectural care is clear. This introduces a complex but maintainable automation pipeline for converting research papers into code.

- 🔐 **Security:**
  - **Path Handling:** Paths are built using string interpolation; user-provided values (`paper_name`, `file_path`) are inserted directly. While not a big risk internally, sanitize these if exposed to end-users or made part of an API (to prevent directory traversal attacks). Consider `os.path.join(...)` consistently.
  - **File I/O:** The agent reads/writes many files in the current working directory. Any integrations should ensure the code can only operate within a controlled folder structure.
  - **No sensitive key handling** or dangerous operations are present.

- 🎨 **Code Style:**
  - **Class and function naming** is consistent and descriptive.
  - **Docstrings** are extensive and follow Google-style conventions.
  - **Consistency:** Minor spelling error: `_PLANING_` should be `_PLANNING_` for English consistency.
  - **Prompt definitions** are clear, multi-line strings for readability.
  - **Type hints** are used extensively and appropriately.
  - **Logging** is used well (consider `logger.exception` rather than `logger.error(e)` for exception tracebacks).

- ⚙️ **Performance:**
  - Most logic is file and I/O bound (loading paper content, generating artifacts). No clear performance bottlenecks unless large files are common.
  - The recursive function `_remove_spans` could become expensive on very highly nested or massive JSON structures, but it's reasonable for expected input.
  - No inefficient loops or unnecessary resource usage.

- 🧩 **Maintainability:**
  - **Modular design:** Each workflow phase (`_planning`, `_analyzing`, `_coding`) is cleanly separated with its own helper(s).
  - **Schema validation** via Pydantic models is robust and improves code reliability.
  - **Explicit phase management** (`status` field) is clear.
  - **Config and Artifact management:** Consistent file naming; may benefit from a constants module or configuration file if paths proliferate further.
  - The process could be unit tested with mocks/subclassing easily thanks to modular methods and testable file outputs.
  - **Extensibility:** New phases or schema elements could be added smoothly.

---

## File: examples/agents/create_paper_to_code_agent.py

- **Overall impression:**
  This is a clear, step-by-step example script to use and test the new agent. Docstrings and commentary are extensive. It includes dummy data setup, example agent usage, and details about expected outputs and workflow.

- 🔐 **Security:**
  - No sensitive data or unsafe operations.
  - Paths are composed from static pieces; user input is not accepted except for environment variables.
  - Dummy paper file created in a controlled location; old outputs are deleted only if a matching directory exists (no wildcards).

- 🎨 **Code Style:**
  - Comments are highly detailed, guiding example users through logic.
  - Variable names are clear and informative.
  - PEP8 is generally observed; minor nits could be made re: line wrapping, but this is acceptable for an example file.
  - Code block is appropriately sectioned for readability.

- ⚙️ **Performance:**
  - Performance impact is minimal. The biggest call-outs are the directory/file existence checks and cleanups, which are fine in this context.

- 🧩 **Maintainability:**
  - Example is robust: handles cleanup from previous runs, provides clear messaging for missing API keys** or runtime error.
  - Extensive inline instructions make this file a great quickstart reference for users.
  - Clean exit attempts in a `finally` block.
  - The decision to keep (not delete) the generated content by default is user-friendly.

---

## File: test/agents/test_paper_to_code_agent.py

- **Overall impression:**
  The tests provide thorough coverage: they test JSON processing, file outputs, and the full multi-phase workflow using mocks for LLM responses. Fixtures are used properly, and the test structure is clear.

- 🔐 **Security:**
  - Inputs/outputs are controlled via pytest's `tmp_path` fixtures; file operations remain in a test-specific sandbox.
  - No risk of leaking sensitive information or interacting with real user-provided files.

- 🎨 **Code Style:**
  - Naming of fixtures, functions, and mock helpers is clear and explicit.
  - Tests are well-documented with comments for each logical section.
  - ruff directive is used appropriately to avoid line-length complaints where needed.

- ⚙️ **Performance:**
  - All test file operations use the `tmp_path` pattern, so tests are isolated and performant.
  - Mocking is leveraged so that expensive LLM/API calls are avoided and the test runs very quickly.

- 🧩 **Maintainability:**
  - Tests are modular and easy to extend.
  - Good use of pytest features (fixtures, patch, assertions).
  - The one minor risk is code duplication for mock Pydantic instance creation, but this is very minor in test code.
  - Suggestion: Adding a test that actually verifies error paths (e.g., insufficient mock responses or corrupt outputs) would further bolster robustness.

---

**Summary:**
- Great structure, clear API, and heavy use of docstrings, type hints, and validation.
- Strong separation of phases in code and tests.
- Only minor actionable suggestions (spelling of PLANING, path/join sanitization, possible log improvements).
- No security, performance, or maintainability concerns of note.

**Overall, an exemplary submission—very nicely done!**
"""





"""
max_token_context = 10000
incremental_review

--- Chunk #1 ---
Files included: ['camel/agents/__init__.py', 'camel/agents/paper_to_code_agent.py', 'test/agents/test_paper_to_code_agent.py']
Message preview: You are an AI code reviewer working in **incremental review mode**, focused on analyzing changes in each file of a single commit.

Your goal is to provide structured, actionable code review feedback f ...

## File: camel/agents/__init__.py

**Overall Impression:**
The file is properly updated to register the new `PaperToCodeAgent` class into the `__all__` list, integrating it into the public agent API. 

- 🔐 **Security:**
  - No security issues found. The change is a simple import and does not affect security.

- 🎨 **Code Style:**
  - The import follows project conventions. The update to `__all__` is consistent and clear.
  - Minor: The trailing comma after the last element in `__all__` is stylistically fine and consistent with the previous code.

- ⚙️ **Performance:**
  - No performance issues; the change is purely structural.

- 🧩 **Maintainability:**
  - Clean integration into existing code structure.
  - No issues observed.

---

## File: camel/agents/paper_to_code_agent.py

**Overall Impression:**
This is a substantial new agent implementation that automates the process of turning a research paper (in JSON or LaTeX format) into a reproducible code project. The class is detailed, modular, and leverages prompt engineering, stepwise planning, analysis, and code generation, with careful orchestration of the pipeline. Documentation is comprehensive.

### Review per Dimension:

- 🔐 **Security:**
  - There is some direct file reading/writing (`open`, `json.load`, `os.makedirs`, `shutil.copy`).
    - **Suggestion:** Input file names and output paths are constructed in a fairly safe way, but if the values for `file_path` or `paper_name` are user-controlled, it might pose a path traversal risk. Recommend sanitizing/validating these values before using them in file system operations.
  - No hardcoded credentials or secrets found.
  - Use of file IO and directory creation appears correct—`os.makedirs` uses `exist_ok=True`, which is good.
  - No shell execution or dangerous external calls.

- 🎨 **Code Style:**
  - Generally excellent: compliant with PEP8, good use of type hints, docstrings for all major methods, nicely formatted.
  - Method names are clear and consistent.
  - Some variable names have minor typos: `"anaylyzing_template"` should be `"analyzing_template"`.
  - The usage of private variables (like `_extract_code_from_content`) is consistent.
  - Method headers and docstrings are detailed and follow best practice.
  - Some long docstrings (especially templates) could potentially be organized into a different module for readability, but it's acceptable here for prompt visibility.

- ⚙️ **Performance:**
  - For large papers, repeated full file reads and dict operations could cause memory issues, but this is likely acceptable for this domain (single-paper at a time).
  - Multiple passes over JSON data (e.g., cleaning/removing spans then writing back) are not problematic for expected input sizes.
  - Extraction and cleaning of YAML and code blocks uses regex—relatively robust but could fail for highly unusual inputs.
  - Use of `.replace("/", "_")` for output file names is a practical approach to avoid directory collisions.

- 🧩 **Maintainability:**
  - The code is well structured and modular, with separate methods for each phase of the agent's operation.
  - Good error handling in content-to-JSON conversion, with multiple fallback attempts and clear warnings when parsing fails.
  - All static prompt templates are kept at the top, aiding reuse and central modification.
  - Extensive use of logging throughout, which will help debugging.
  - The class is heavily documented, which aids maintainability.
  - The agent is tightly coupled to CAMEL-specific infrastructure (memory, messages, model backend), so portability to another framework would require some rework, but this is expected.
  - Code assumes certain response structures in the LLM outputs; if the prompt or model changes, downstream processing might need to be updated.
  - Minor: Duplicated code in `_content_to_json` for string cleaning—could extract to helper functions for clarity.
  - Minor typo in the comment: "anaylyzing_template" (should be "analyzing_template").

**General Suggestions:**
- Consider minimal input sanitization for `file_path` and `paper_name` to avoid potential path traversal (security).
- Fix the typo `"anaylyzing_template"` to `"analyzing_template"` for clarity and professionalism.
- If prompts become unwieldy, consider storing large templates in resource files or constants module.
- In error messages ("Failed to parse JSON with all approaches"), consider raising exceptions or failing more visibly in critical pipelines. 

---

## File: test/agents/test_paper_to_code_agent.py

**Overall Impression:**
The file adds a test (with `pytest`) for the new `PaperToCodeAgent`. The test creates a PaperToCodeAgent with a sample paper and runs the full pipeline.

- 🔐 **Security:**
  - No issues found. This is a test file with no external risks.

- 🎨 **Code Style:**
  - Uses pytest conventions; function names and structure are good.
  - The commented-out lines for model instantiation are acceptable in a test template.
  - The test is not very robust: it merely runs the main function without assertions. Ideally, a good test would check outputs, but this is a reasonable first step for an integration test.
  - Uses `if __name__ == "__main__":` for standalone running—fine for debugging, but usually pytest-based tests don't need this.
  - Code style (imports, spacing, naming) looks good.

- ⚙️ **Performance:**
  - Running this test will invoke a full LLM-based pipeline, which could be slow and costly. Consider marking it as "slow" or "integration" in future.
  - No performance issues for a test stub.

- 🧩 **Maintainability:**
  - As a test stub, it's okay. Could be improved by asserting properties, output files, or side effects to ensure full correctness.
  - Uses path construction that is relatively portable.

---

**Summary:**
- The main agent is robust, well-documented, follows good design practices, with minor style nits (typo in variable name).
- Potential risk: If user inputs for file paths are untrusted, some path validation/sanitization should be added.
- Test coverage is started, but could be improved with actual assertions and more granular checks.
- Prompts are hardcoded into the Python file—they're clearly documented, but might be moved elsewhere if they grow further.

Overall, this is a high-quality addition, showing careful engineering and modularity. Only minor issues need addressing.

"""



