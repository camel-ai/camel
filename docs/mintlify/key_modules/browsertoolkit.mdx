---
title: "Browser Toolkit"
icon: "globe"
---

<Note type="info" title="What is the Browser Toolkit?">
  The <b>Browser Toolkit</b> provides a powerful set of tools to automate and interact with web browsers. It allows CAMEL agents to perform complex web-based tasks, from simple page navigation to intricate form submissions and data extraction.
</Note>

<CardGroup cols={2}>
  <Card title="Two-Agent System" icon="users">
    Uses a sophisticated two-agent system: a `planning_agent` to create and refine high-level plans, and a `web_agent` to observe the screen and execute low-level actions.
  </Card>
  <Card title="Visual Reasoning" icon="image">
    The `web_agent` can analyze "Set-of-Marks" (SoM) screenshots, which are visual representations of the page with interactive elements highlighted, enabling it to perform complex visual reasoning.
  </Card>
  <Card title="Persistent Sessions" icon="cookie">
    Supports persistent browser sessions by saving and loading cookies and user data, allowing the agent to stay logged into websites across multiple sessions.
  </Card>
  <Card title="Video Analysis" icon="video">
    Can analyze videos on the current page (e.g., YouTube) to answer questions about their content, leveraging the `VideoAnalysisToolkit`.
  </Card>
</CardGroup>

## Initialization

To get started, initialize the `BrowserToolkit`. You can configure the underlying models for the planning and web agents.

<Tabs>
<Tab title="Default">
```python
from camel.toolkits import BrowserToolkit

# Initialize with default models
browser_toolkit = BrowserToolkit()
```
</Tab>
<Tab title="Custom Models">
```python
from camel.toolkits import BrowserToolkit
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

# Define custom models for the agents (use latest OpenAI models)
web_agent_model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_5_MINI,
)
planning_agent_model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.O4_MINI,
)

browser_toolkit = BrowserToolkit(
    web_agent_model=web_agent_model,
    planning_agent_model=planning_agent_model,
)
```
</Tab>
</Tabs>

## Core Functionality: `browse_url`

The main entry point for the toolkit is the `browse_url` function. It takes a high-level task and a starting URL, and then autonomously navigates the web to complete the task.

<Card title="Example: Researching a Topic" icon="magnifying-glass">
```python
task_prompt = "Find the main contributions of the paper 'Sparks of AGI' by Microsoft Research."
start_url = "https://www.google.com"

# The agent will navigate from Google, find the paper, and extract the information.
result = browser_toolkit.browse_url(
    task_prompt=task_prompt,
    start_url=start_url,
)

print(result)
```
</Card>

## How It Works: The Two-Agent System

The `browse_url` function orchestrates a loop between the `planning_agent` and the `web_agent`.

<Steps>
<Step title="Planning">
The `planning_agent` creates a high-level plan to accomplish the task.
</Step>
<Step title="Observation">
The `web_agent` observes the current page by taking a "Set-of-Marks" (SoM) screenshot.
</Step>
<Step title="Action">
Based on the observation and the plan, the `web_agent` decides on the next action to take (e.g., click, type, scroll).
</Step>
<Step title="Execution">
The toolkit executes the action and the loop repeats.
</Step>
<Step title="Replanning">
If the `web_agent` gets stuck, the `planning_agent` can re-evaluate the situation and create a new plan.
</Step>
</Steps>

## Advanced Usage

### Persistent Sessions
You can maintain login sessions across runs by providing a path to a `cookies.json` file or a `user_data_dir`.

<Card title="Using a Persistent Session" icon="cookie">
```python
# The toolkit will save cookies and local storage to this file
cookie_path = "./my_browser_session.json"

# First run: Log in to a website
# browser_toolkit = BrowserToolkit(cookie_json_path=cookie_path)
# browser_toolkit.browse_url(task_prompt="Log in to my account...", start_url="...")

# Subsequent runs: The agent will be logged in automatically
browser_toolkit_loggedin = BrowserToolkit(cookie_json_path=cookie_path)
```
</Card>

### Video Analysis

The toolkit can answer questions about videos on a webpage.

<Card title="Asking a Question About a YouTube Video" icon="video">
```python
# First, navigate to the video
browser_toolkit.browse_url(task_prompt="Navigate to a specific YouTube video", start_url="...")

# Then, ask a question about it
# Note: This is an example of how you might use the underlying BaseBrowser.
# The browse_url function would orchestrate this automatically.
question = "What is the main topic of this video?"
answer = browser_toolkit.browser.ask_question_about_video(question=question)

print(answer)
```
</Card> 