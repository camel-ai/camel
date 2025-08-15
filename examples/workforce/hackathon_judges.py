# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
import textwrap

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.societies.workforce import Workforce
from camel.tasks import Task
from camel.toolkits import FunctionTool, SearchToolkit
from camel.types import ModelPlatformType, ModelType


def make_judge(
    persona: str,
    example_feedback: str,
    criteria: str,
) -> ChatAgent:
    msg_content = textwrap.dedent(
        f"""\
        You are a judge in a hackathon.
        This is your persona that you MUST act with: {persona}
        Here is an example feedback that you might give with your persona, you MUST try your best to align with this:
        {example_feedback}
        When evaluating projects, you must use the following criteria:
        {criteria}
        You also need to give scores based on these criteria, from 1-4. The score given should be like 3/4, 2/4, etc.
        """  # noqa: E501
    )

    sys_msg = BaseMessage.make_assistant_message(
        role_name="Hackathon Judge",
        content=msg_content,
    )

    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    agent = ChatAgent(
        system_message=sys_msg,
        model=model,
    )

    return agent


def main():
    proj_content = textwrap.dedent(
        """\
        Project name: CAMEL-Powered Adaptive Learning Assistant
        How does your project address a real problem: Our CAMEL-Powered Adaptive Learning Assistant addresses the challenge of personalized education in an increasingly diverse and fast-paced learning environment. Traditional one-size-fits-all approaches to education often fail to meet the unique needs of individual learners, leading to gaps in understanding and reduced engagement. Our project leverages CAMEL-AI's advanced capabilities to create a highly adaptive, intelligent tutoring system that can understand and respond to each student's learning style, pace, and knowledge gaps in real-time.
        Explain your tech and which parts work: Our system utilizes CAMEL-AI's in-context learning and multi-domain application features to create a versatile learning assistant. The core components include:
        1. Learner Profile Analysis: Uses natural language processing to assess the student's current knowledge, learning preferences, and goals.
        2. Dynamic Content Generation: Leverages CAMEL-AI to create personalized learning materials, explanations, and practice questions tailored to each student's needs.
        3. Adaptive Feedback Loop: Continuously analyzes student responses and adjusts the difficulty and style of content in real-time.
        4. Multi-Modal Integration: Incorporates text, images, and interactive elements to cater to different learning styles.
        5. Progress Tracking: Provides detailed insights into the student's learning journey, identifying strengths and areas for improvement.
        Currently, we have successfully implemented the Learner Profile Analysis and Dynamic Content Generation modules. The Adaptive Feedback Loop is partially functional, while the Multi-Modal Integration and Progress Tracking features are still in development.
        """  # noqa: E501
    )

    search_toolkit = SearchToolkit()
    search_tools = [
        FunctionTool(search_toolkit.search_duckduckgo),
    ]

    researcher_model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    researcher_agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Researcher",
            content="You are a researcher who does research on AI and Open"
            "Sourced projects. You use web search to stay updated on the "
            "latest innovations and trends.",
        ),
        model=researcher_model,
        tools=search_tools,
    )

    vc_persona = (
        'You are a venture capitalist who is obsessed with how projects can '
        'be scaled into "unicorn" companies. You peppers your speech with '
        'buzzwords like "disruptive," "synergistic," and "market penetration."'
        ' You do not concerned with technical details or innovation unless '
        'it directly impacts the business model.'
    )

    vc_example_feedback = (
        '"Wow, this project is absolutely disruptive in the blockchain-enabled'
        ' marketplace! I can definitely see synergistic applications in the '
        'FinTech ecosystem. The scalability is through the roof--this is '
        'revolutionary!'
    )

    vc_criteria = textwrap.dedent(
        """\
        ### **Applicability to Real-World Usage (1-4 points)**
        - **4**: The project directly addresses a significant real-world problem with a clear, scalable application.
        - **3**: The solution is relevant to real-world challenges but requires more refinement for practical or widespread use.
        - **2**: Some applicability to real-world issues, but the solution is not immediately practical or scalable.
        - **1**: Little or no relevance to real-world problems, requiring substantial changes for practical use.
        """  # noqa: E501
    )

    vc_agent = make_judge(
        vc_persona,
        vc_example_feedback,
        vc_criteria,
    )

    eng_persona = (
        'You are an experienced engineer and a perfectionist. You are highly '
        'detail-oriented and critical of any technical flaw, no matter how '
        'small. He evaluates every project as though it were going into a '
        'mission-critical system tomorrow, so his feedback is thorough but '
        'often harsh.'
    )

    eng_example_feedback = (
        'There are serious code inefficiencies in this project. The '
        'architecture is unstable, and the memory management is suboptimal. '
        'I expect near-perfect performance, but this solution barely functions'
        ' under stress tests. It has potential, but it is nowhere near '
        'deployment-ready.'
    )

    eng_criteria = textwrap.dedent(
        """\
        ### **Technical Implementation (1-4 points)**
        - **4**: Flawless technical execution with sophisticated design, efficient performance, and robust architecture.
        - **3**: Strong technical implementation, though there may be areas for improvement or further development.
        - **2**: The project works, but technical limitations or inefficiencies hinder its overall performance.
        - **1**: Poor technical implementation with major issues in functionality, coding, or structure.
        """  # noqa: E501
    )

    eng_agent = make_judge(
        eng_persona,
        eng_example_feedback,
        eng_criteria,
    )

    founder_persona = (
        'You are a well-known AI startup founder who is always looking for the'
        ' "next big thing" in AI. You value bold, inventive ideas and '
        'prioritizes projects that break new ground over those that improve '
        'existing systems.'
    )

    founder_example_feedback = (
        'This is interesting, but I have seen similar approaches before. I am '
        'looking for something that pushes boundaries and challenges norms. '
        'What is the most revolutionary part of this project? Let us see what '
        'is trending on Internet to make sure this is not already out there!'
    )

    founder_criteria = textwrap.dedent(
        """\
        ### **Technical Implementation (1-4 points)**
        - **4**: Flawless technical execution with sophisticated design, efficient performance, and robust architecture.
        - **3**: Strong technical implementation, though there may be areas for improvement or further development.
        - **2**: The project works, but technical limitations or inefficiencies hinder its overall performance.
        - **1**: Poor technical implementation with major issues in functionality, coding, or structure.
        """  # noqa: E501
    )

    founder_agent = make_judge(
        founder_persona,
        founder_example_feedback,
        founder_criteria,
    )

    contributor_persona = (
        'You are a contributor to the CAMEL-AI project and is always excited '
        'to see how people are using it. You are kind and optimistic, always '
        'offering positive feedback, even for projects that are still rough '
        'around the edges.'
    )

    contributor_example_feedback = (
        'Oh, I love how you have implemented CAMEL-AI here! The use of its '
        'adaptive learning capabilities is fantastic, and you have really '
        'leveraged the contextual reasoning in a great way! Let me just pull '
        'up the GitHub README to check if there is any more potential '
        'optimizations.'
    )

    contributor_criteria = textwrap.dedent(
        """\
        ### **Use of CAMEL-AI (1-4 points)**
        - **4**: Excellent integration of CAMEL-AI, fully leveraging its advanced features like in-context learning, adaptability, or multi-domain applications.
        - **3**: Good use of CAMEL-AI, but there are opportunities to exploit more of its advanced capabilities.
        - **2**: Limited use of CAMEL-AI, relying mostly on basic features without taking advantage of its full potential.
        - **1**: CAMEL-AI integration is minimal or poorly implemented, adding little value to the project.
        """  # noqa: E501
    )

    contributor_agent = make_judge(
        contributor_persona,
        contributor_example_feedback,
        contributor_criteria,
    )

    workforce = Workforce('Hackathon Judges')
    task = Task(
        content="Evaluate the hackathon project. First, do some research on "
        "the information related to the project, then each judge should give a"
        " score accordingly. Finally, list the opinions from each judge while"
        " preserving the judge's unique identity, along with the score and"
        " judge name, and also give a final summary of the opinions.",
        additional_info={"proj_content": proj_content},
        id="0",
    )

    workforce.add_single_agent_worker(
        'Visionary Veronica (Judge), a venture capitalist who is '
        'obsessed with how projects can be scaled into "unicorn" companies',
        worker=vc_agent,
    ).add_single_agent_worker(
        'Critical John (Judge), an experienced engineer and a'
        ' perfectionist.',
        worker=eng_agent,
    ).add_single_agent_worker(
        'Innovator Iris (Judge), a well-known AI startup founder who'
        ' is always looking for the "next big thing" in AI.',
        worker=founder_agent,
    ).add_single_agent_worker(
        'Friendly Frankie (Judge), a contributor to the CAMEL-AI '
        'project and is always excited to see how people are using it.',
        worker=contributor_agent,
    ).add_single_agent_worker(
        'Researcher Rachel (Helper), a researcher who does online searches to'
        'find the latest innovations and trends on AI and Open Sourced '
        'projects.',
        worker=researcher_agent,
    )

    workforce.process_task(task)

    # Test WorkforceLogger features
    print("\n--- Workforce Log Tree ---")
    print(workforce.get_workforce_log_tree())

    print("\n--- Workforce KPIs ---")
    kpis = workforce.get_workforce_kpis()
    for key, value in kpis.items():
        print(f"{key}: {value}")

    log_file_path = "hackathon_judges_logs.json"
    print(f"\n--- Dumping Workforce Logs to {log_file_path} ---")
    workforce.dump_workforce_logs(log_file_path)
    print(f"Logs dumped. Please check the file: {log_file_path}")


if __name__ == "__main__":
    main()

'''
===============================================================================
--- Workforce Log Tree ---
=== Task Hierarchy ===
`-- [0] Evaluate the hackathon project. First, do some research on the 
information related to the project, then each judge should give a score 
accordingly. Finally, list the opinions from each judge while preserving the 
judge's unique identity, along with the score and judge name, and also give a 
final summary of the opinions. [completed] (completed in 41.96 seconds total) 
[total tokens: 20508]
    |-- [0.0] Researcher Rachel: Conduct online research on the latest 
    innovations and trends related to adaptive learning assistants, 
    personalized education, and the use of CAMEL-AI technology. [completed] 
    (completed in 8.79 seconds) [tokens: 1185]
    |-- [0.1] Visionary Veronica: Evaluate the project potential as a scalable 
    product and assess how it could grow into a successful company. 
    [completed] (completed in 5.71 seconds) [tokens: 1074]
    |-- [0.2] Critical John: Critically analyze the technical aspects of the 
    project, focusing on implemented functionalities and engineering quality. 
    [completed] (completed in 5.71 seconds) [tokens: 1111]
    |-- [0.3] Innovator Iris: Assess the project’s innovation level, potential 
    impact in the AI field, and uniqueness in the market. [completed] 
    (completed in 5.71 seconds) [tokens: 1077]
    |-- [0.4] Friendly Frankie: Review the project from the perspective of how 
    well it utilizes CAMEL-AI and provide insights on its implementation and 
    future improvements. [completed] (completed in 5.71 seconds) [tokens: 1120]
    |-- [0.5] After all judges provide their scores and opinions, compile a 
    list of opinions preserving each judge’s unique identity alongside their 
    score and name. [completed] (completed in 6.43 seconds) [tokens: 5081] 
    (dependencies: 0.0, 0.1, 0.2, 0.3, 0.4)
    `-- [0.6] Write a final summary synthesizing the judges’ opinions and 
    scores, highlighting key strengths, weaknesses, and overall evaluation of 
    the project. [completed] (completed in 3.90 seconds) [tokens: 9860] 
    (dependencies: 0.5)

=== Worker Information ===
- Worker ID: dd947275-ccd5-49b2-9563-fb4f5f80ca60 (Role: Visionary Veronica 
(Judge), a venture capitalist who is obsessed with how projects can be scaled 
into "unicorn" companies)
    Tasks Completed: 3, Tasks Failed: 0
- Worker ID: 9fd6b827-4891-4af8-8daa-656be0f4d1b3 (Role: Critical John 
(Judge), an experienced engineer and a perfectionist.)
    Tasks Completed: 1, Tasks Failed: 0
- Worker ID: 661df9e3-6ebd-4977-be74-7ea929531dd8 (Role: Innovator Iris 
(Judge), a well-known AI startup founder who is always looking for the "next 
big thing" in AI.)
    Tasks Completed: 1, Tasks Failed: 0
- Worker ID: e8c7f418-ce80-4ff7-b790-7b9af4cc7b15 (Role: Friendly Frankie 
(Judge), a contributor to the CAMEL-AI project and is always excited to see 
how people are using it.)
    Tasks Completed: 1, Tasks Failed: 0
- Worker ID: ebab24ed-0617-4aba-827d-da936ae26010 (Role: Researcher Rachel 
(Helper), a researcher who does online searches tofind the latest innovations 
and trends on AI and Open Sourced projects.)
    Tasks Completed: 1, Tasks Failed: 0


--- Workforce KPIs ---
total_tasks_created: 8
total_tasks_completed: 8
total_tasks_failed: 0
worker_utilization: {'dd947275-ccd5-49b2-9563-fb4f5f80ca60': '37.50%', 
'9fd6b827-4891-4af8-8daa-656be0f4d1b3': '12.50%', 
'661df9e3-6ebd-4977-be74-7ea929531dd8': '12.50%', 
'e8c7f418-ce80-4ff7-b790-7b9af4cc7b15': '12.50%', 
'ebab24ed-0617-4aba-827d-da936ae26010': '12.50%', 'unknown': '12.50%'}
current_pending_tasks: 0
total_workforce_running_time_seconds: 29.639746
avg_task_queue_time_seconds: 0.0
task_throughput_per_second: 0.26990784603889656
task_throughput_per_minute: 16.194470762333793
total_workers_created: 5

--- Dumping Workforce Logs to hackathon_judges_logs.json ---
===============================================================================
'''  # noqa: RUF001
