---
title: "Societies"
description: "Collaborative agent frameworks in CAMEL: autonomous social behaviors, role-based task solving, and turn-based agent societies."
icon: people-group
---

<Note type="info" title="What is the Society Module?">
  The <b>society module</b> simulates agent social behaviors and collaborative workflows.<br/>
  It powers <b>autonomous, multi-role agents</b> that can plan, debate, critique, and solve tasks together, minimizing human intervention while maximizing alignment with your goals.
</Note>

<Card icon="users" title="Society Concepts: How Do AI Agents Interact?" className="my-6">
  <b>Task:</b> An objective or idea, given as a simple prompt.<br/>
  <b>AI User:</b> The role responsible for providing instructions or challenges.<br/>
  <b>AI Assistant:</b> The role tasked with generating solutions, plans, or step-by-step responses.<br/>
  <b>Critic (optional):</b> An agent that reviews or critiques the assistant's responses for quality control.<br/><br/>
</Card>

<div style={{ display: "flex", gap: "1.5rem", flexWrap: "wrap" }}>
  <Card icon="repeat" title="RolePlaying" style={{ flex: "1 1 320px" }}>
    <b>Turn-based, prompt-engineered, zero-role-flip agent collaboration.</b>
    <ul>
      <li>Guards against role-flipping, infinite loops, vague responses</li>
      <li>Structured, strict turn-taking—user and assistant never switch</li>
      <li>Supports optional task planners, critics, and meta-reasoning</li>
      <li>Every message follows a system-enforced structure</li>
    </ul>
    <div>
      <b>Built-in Prompt Rules:</b>
      <ul style={{ marginBottom: 0 }}>
        <li>Never forget you are <code>&lt;ASSISTANT_ROLE&gt;</code>, I am <code>&lt;USER_ROLE&gt;</code></li>
        <li>Never flip roles or instruct me</li>
        <li>Decline impossible or unsafe requests, explain why</li>
        <li>Always answer as: <code>Solution: &lt;YOUR_SOLUTION&gt;</code></li>
        <li>Always end with: <code>Next request.</code></li>
      </ul>
    </div>
  </Card>
</div>

## 🧩 RolePlaying Attributes

<AccordionGroup>
  <Accordion title="All RolePlaying Parameters">
    <table>
      <thead>
        <tr>
          <th>Attribute</th>
          <th>Type</th>
          <th>Description</th>
        </tr>
      </thead>
      <tbody>
        <tr><td>assistant_role_name</td><td>str</td><td>Name of assistant's role</td></tr>
        <tr><td>user_role_name</td><td>str</td><td>Name of user's role</td></tr>
        <tr><td>critic_role_name</td><td>str</td><td>Name of critic's role (optional)</td></tr>
        <tr><td>task_prompt</td><td>str</td><td>Prompt for the main task</td></tr>
        <tr><td>with_task_specify</td><td>bool</td><td>Enable task specification agent</td></tr>
        <tr><td>with_task_planner</td><td>bool</td><td>Enable task planner agent</td></tr>
        <tr><td>with_critic_in_the_loop</td><td>bool</td><td>Include critic in conversation loop</td></tr>
        <tr><td>critic_criteria</td><td>str</td><td>How the critic scores/evaluates outputs</td></tr>
        <tr><td>model</td><td>BaseModelBackend</td><td>Model backend for responses</td></tr>
        <tr><td>task_type</td><td>TaskType</td><td>Type/category of the task</td></tr>
        <tr><td>assistant_agent_kwargs</td><td>Dict</td><td>Extra options for assistant agent</td></tr>
        <tr><td>user_agent_kwargs</td><td>Dict</td><td>Extra options for user agent</td></tr>
        <tr><td>task_specify_agent_kwargs</td><td>Dict</td><td>Extra options for task specify agent</td></tr>
        <tr><td>task_planner_agent_kwargs</td><td>Dict</td><td>Extra options for task planner agent</td></tr>
        <tr><td>critic_kwargs</td><td>Dict</td><td>Extra options for critic agent</td></tr>
        <tr><td>sys_msg_generator_kwargs</td><td>Dict</td><td>Options for system message generator</td></tr>
        <tr><td>extend_sys_msg_meta_dicts</td><td>List[Dict]</td><td>Extra metadata for system messages</td></tr>
        <tr><td>extend_task_specify_meta_dict</td><td>Dict</td><td>Extra metadata for task specification</td></tr>
        <tr><td>output_language</td><td>str</td><td>Target output language</td></tr>
      </tbody>
    </table>
  </Accordion>
</AccordionGroup>

<Card icon="zap" title="Get Started: RolePlaying in Action" className="my-6">
  <b>Example: Turn-based multi-agent chat with custom roles and live output colors.</b>
  <br/><br/>
  ~~~python
from colorama import Fore
from camel.societies import RolePlaying
from camel.utils import print_text_animated

def main(model=None, chat_turn_limit=50) -> None:
    # Initialize a session for developing a trading bot
    task_prompt = "Develop a trading bot for the stock market"
    role_play_session = RolePlaying(
        assistant_role_name="Python Programmer",
        assistant_agent_kwargs=dict(model=model),
        user_role_name="Stock Trader",
        user_agent_kwargs=dict(model=model),
        task_prompt=task_prompt,
        with_task_specify=True,
        task_specify_agent_kwargs=dict(model=model),
    )

    # Print initial system messages
    print(
        Fore.GREEN
        + f"AI Assistant sys message:\\n{role_play_session.assistant_sys_msg}\\n"
    )
    print(
        Fore.BLUE + f"AI User sys message:\\n{role_play_session.user_sys_msg}\\n"
    )

    print(Fore.YELLOW + f"Original task prompt:\\n{task_prompt}\\n")
    print(
        Fore.CYAN
        + "Specified task prompt:"
        + f"\\n{role_play_session.specified_task_prompt}\\n"
    )
    print(Fore.RED + f"Final task prompt:\\n{role_play_session.task_prompt}\\n")

    n = 0
    input_msg = role_play_session.init_chat()

    # Turn-based simulation
    while n < chat_turn_limit:
        n += 1
        assistant_response, user_response = role_play_session.step(input_msg)

        if assistant_response.terminated:
            print(
                Fore.GREEN
                + (
                    "AI Assistant terminated. Reason: "
                    f"{assistant_response.info['termination_reasons']}."
                )
            )
            break
        if user_response.terminated:
            print(
                Fore.GREEN
                + (
                    "AI User terminated. "
                    f"Reason: {user_response.info['termination_reasons']}."
                )
            )
            break

        print_text_animated(
            Fore.BLUE + f"AI User:\\n\\n{user_response.msg.content}\\n"
        )
        print_text_animated(
            Fore.GREEN + "AI Assistant:\\n\\n"
            f"{assistant_response.msg.content}\\n"
        )

        if "CAMEL_TASK_DONE" in user_response.msg.content:
            break

        input_msg = assistant_response.msg

if __name__ == "__main__":
    main()
  ~~~
</Card>

<AccordionGroup>
  <Accordion title="Tips & Best Practices">
    <ul>
      <li>Use <b>RolePlaying</b> for most multi-agent conversations, with or without a critic.</li>
      <li>Define specific roles and prompt-guardrails for your agents—structure is everything!</li>
      <li>Try <b>BabyAGI</b> when you want open-ended, research-oriented, or autonomous projects.</li>
      <li>Leverage the <code>with_task_specify</code> and <code>with_task_planner</code> options for highly complex tasks.</li>
      <li>Monitor for infinite loops—every agent response should have a clear next step or end.</li>
    </ul>
  </Accordion>
  <Accordion title="More Examples & Advanced Use">
    <ul>
      <li>Check <code>[examples/society/](https://github.com/camel-ai/camel/tree/master/examples/runtimes)</code> in the CAMEL repo for advanced agent society demos.</li>
      <li>Explore <b>critic-in-the-loop</b> setups for higher accuracy and safety.</li>
      <li>Integrate toolkits or external APIs into agent society loops for real-world workflows.</li>
    </ul>
  </Accordion>
</AccordionGroup>
