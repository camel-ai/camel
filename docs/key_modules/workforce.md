---
title: "Workforce"
icon: users
---

<Card title="Concept" icon="users">
Workforce is CAMEL-AI’s multi-agent teamwork engine.

Instead of relying on a single agent, Workforce lets you organize a *team* of specialized agents—each with its own strengths—under a single, coordinated system. You can quickly assemble, configure, and launch collaborative agent “workforces” for any task that needs parallelization, diverse expertise, or complex workflows.

With Workforce, agents plan, solve, and verify work together—like a project team in an organization, but fully automated.

<Note type="info">
**Key advantages of Workforce:**  
- Instantly scale from single-agent to multi-agent workflows  
- Built-in coordination, planning, and failure recovery  
- Ideal for hackathons, evaluations, code review, brainstorming, and more  
- Configure roles, toolsets, and communication patterns for *any* scenario  
</Note>
</Card>

<Card title="See More: Hackathon Judge Committee Example" icon="link" href="https://colab.research.google.com/drive/18ajYUMfwDx3WyrjHow3EvUMpKQDcrLtr?usp=sharing">
  Check out our in-depth Workforce example:  
  <b>Create a Hackathon Judge Committee with Workforce</b>
</Card>

---

## System Design

### Architecture: How Workforce Works

Workforce uses a **hierarchical, modular design** for real-world team problem-solving:

See how the coordinator and task planner agents orchestrate a multi-agent workflow:

![Workforce Architecture Diagram](https://i.postimg.cc/jSnjsN57/Wechat-IMG1592.jpg)

- **Workforce:** The “team” as a whole.
- **Worker nodes:** Individual contributors—each node can contain one or more agents, each with their own capabilities.
- **Coordinator agent:** The “project manager”—routes tasks to worker nodes based on their role and skills.
- **Task planner agent:** The “strategy lead”—breaks down big jobs into smaller, doable subtasks and organizes the workflow.

### Communication: A Shared Task Channel

- Every Workforce gets a **shared task channel** when it’s created.
- **How it works:**
  - All tasks are posted into this channel.
  - Worker nodes “listen” and accept their assigned tasks.
  - Results are posted back to the channel, where they’re available as dependencies for the next steps.

*This design lets agents build on each other's work and ensures no knowledge is lost between steps.*

### Failure Handling: Built-In Robustness

Workforce is designed to handle failures and recover gracefully:

- If a worker fails a task, the coordinator agent will:
  - **Decompose and retry:** Break the task into even smaller pieces and reassign.
  - **Escalate:** If the task keeps failing, create a new worker designed for that problem.
- To prevent infinite loops, if a task has failed or been decomposed more than a set number of times (default: 3), Workforce will automatically halt that workflow.

<Tip>
  <b>Tip:</b> Workforce automatically stops stuck workflows—so you don’t waste compute or get caught in agent loops!
</Tip>

---

<Card title="Quickstart: Build Your First Workforce" icon="rocket">

<Steps>
  <Step title="Create a Workforce Instance">
    To begin, import and create a new Workforce:

    ```python
    from camel.societies.workforce import Workforce

    # Create a workforce instance
    workforce = Workforce("A Simple Workforce")
    ```

    <Tip>
      For quick setups, just provide the description.  
      For advanced workflows, you can pass in custom worker lists or configure the coordinator and planner agents.
    </Tip>
  </Step>

  <Step title="Add Worker Nodes">
    Now add your worker agents.  
    (Example: a `ChatAgent` for web search, named `search_agent`.)

    ```python
    # Add a worker agent to the workforce
    workforce.add_single_agent_worker(
        "An agent that can do web searches",
        worker=search_agent,
    )
    ```

    **Chain multiple agents for convenience:**
    ```python
    workforce.add_single_agent_worker(
        "An agent that can do web searches",
        worker=search_agent,
    ).add_single_agent_worker(
        "Another agent",
        worker=another_agent,
    ).add_single_agent_worker(
        "Yet another agent",
        worker=yet_another_agent,
    )
    ```

    <Tip>
      The *description* is important!  
      The coordinator uses it to assign tasks—so keep it clear and specific.
    </Tip>
  </Step>

  <Step title="Start the Workforce and Solve Tasks">
    Define a task and let the workforce handle it:

    ```python
    from camel.tasks import Task

    # The id can be any string
    task = Task(
        content="Make a travel plan for a 3-day trip to Paris.",
        id="0",
    )

    # Process the task with the workforce
    task = workforce.process_task(task)

    # See the result
    print(task.result)
    ```
  </Step>
</Steps>
</Card>

---

<CardGroup cols={2}>
  <Card
    title="Cookbook: Hackathon Judge Committee"
    icon="bookmark"
    href="https://colab.research.google.com/drive/18ajYUMfwDx3WyrjHow3EvUMpKQDcrLtr?usp=sharing"
  >
    See a real-world multi-agent workflow with Workforce.
  </Card>
  <Card
    title="API Reference"
    icon="book"
    href="/reference/#societies.workforce"
  >
    Full documentation for advanced usage and configuration.
  </Card>
</CardGroup>

