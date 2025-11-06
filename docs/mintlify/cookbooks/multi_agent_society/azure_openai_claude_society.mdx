---
title: "🍳 CAMEL Cookbook: Building a Collaborative AI Research Society"
---

## Claude 4 + Azure OpenAI Collaboration for ARENA AI Alignment Research

<div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: "1rem", marginBottom: "2rem" }}>
  <a href="https://www.camel-ai.org/">
    <img src="https://i.postimg.cc/KzQ5rfBC/button.png" width="150" alt="CAMEL Homepage"/>
  </a>
  <a href="https://discord.camel-ai.org">
    <img src="https://i.postimg.cc/L4wPdG9N/join-2.png" width="150" alt="Join Discord"/>
  </a>
</div>  

⭐ *Star us on [GitHub](https://github.com/camel-ai/camel), join our [Discord](https://discord.camel-ai.org), or follow us on [X](https://x.com/camelaiorg)*

---

## 📋 Overview

This cookbook demonstrates how to create a collaborative multi-agent society using CAMEL-AI, bringing together Claude 4 and Azure OpenAI models to research AI alignment topics from the ARENA curriculum.

Our society consists of 4 specialized AI researchers with distinct personas and expertise areas.

## So, Let's catapault our way right in 🧚

## 🛠️ Dependencies and Setup
First, let's install the required dependencies and handle the notebook environment:


```python
!pip install camel-ai['0.2.64'] anthropic
```


```python
import textwrap
import os
from getpass import getpass
from typing import Dict, Any

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.models.azure_openai_model import AzureOpenAIModel
from camel.tasks import Task
from camel.toolkits import FunctionTool, SearchToolkit
from camel.types import ModelPlatformType, ModelType
from camel.societies.workforce import Workforce
```

Prepare API keys: Azure OpenAI, Claude (Anthropic), and optionally Google Search



```python
# Ensuring API Keys are set
if not os.getenv("AZURE_OPENAI_API_KEY"):
  print("AZURE OPENAI API KEY is required to proceed.")
  azure_openai_api_key = getpass("Enter your Azure OpenAI API Key: ")
  os.environ["AZURE_OPENAI_API_KEY"] = azure_openai_api_key

if not os.getenv("AZURE_OPENAI_ENDPOINT"):
  print("Azure OpenAI Endpoint is required to proceed.")
  azure_openai_endpoint = input("Enter your Azure OpenAI Endpoint: ")
  os.environ["AZURE_OPENAI_ENDPOINT"] = azure_openai_endpoint

if not os.getenv("ANTHROPIC_API_KEY"):
  print("ANTHROPIC API KEY is required to proceed.")
  anthropic_api_key = getpass("Enter your Anthropic API Key: ")
  os.environ["ANTHROPIC_API_KEY"] = anthropic_api_key

optional_keys_setup = input("Setup optional API Keys for Google search functionality?(y/n): ").lower()

if "y" in optional_keys_setup:
  if not os.getenv("GOOGLE_API_KEY"):
    print("[OPTIONAL] Provide a GOOGLE CLOUD API KEY for google search.")
    google_api_key = getpass("Enter your Google API KEY: ")
    os.environ["GOOGLE_API_KEY"] = google_api_key

  if not os.getenv("SEARCH_ENGINE_ID"):
    print("[OPTIONAL] Provide a search engine ID for google search.")
    search_engine_id = getpass("Enter your Search Engine ID: ")
    os.environ["SEARCH_ENGINE_ID"] = search_engine_id

```

### What this does:

- Imports all necessary CAMEL-AI components
- Handles async operations for notebook environments
- Sets up typing hints for better code clarity


## 🏗️ Core Society Class Structure
Let's define our main research society class:


```python
class ARENAResearchSociety:
    """
    A collaborative CAMEL society between Claude 4 and Azure OpenAI
    for researching the ARENA AI alignment curriculum.
    """

    def __init__(self):
        self.workforce = None
        self.setup_api_keys()
```

### What this does:

- Creates the main class that will orchestrate our AI research society
- Initializes with API key setup to ensure proper authentication
- Prepares the workforce variable for later agent assignment

## 🔑 API Configuration Management
Configure all necessary API keys and endpoints:


```python
def setup_api_keys(self):
    """Setup API keys for Azure OpenAI and Claude"""
    print("🔧 Setting up API keys...")

    # Azure OpenAI configuration
    if not os.getenv("AZURE_OPENAI_API_KEY"):
        azure_api_key = getpass("Please input your Azure OpenAI API key: ")
        os.environ["AZURE_OPENAI_API_KEY"] = azure_api_key

    if not os.getenv("AZURE_OPENAI_ENDPOINT"):
        azure_endpoint = getpass("Please input your Azure OpenAI endpoint: ")
        os.environ["AZURE_OPENAI_ENDPOINT"] = azure_endpoint

    if not os.getenv("AZURE_DEPLOYMENT_NAME"):
        deployment_name = getpass("Please input your Azure deployment name (e.g., div-o4-mini): ")
        os.environ["AZURE_DEPLOYMENT_NAME"] = deployment_name

    # Set OPENAI_API_KEY for compatibility (use Azure key)
    os.environ["OPENAI_API_KEY"] = os.getenv("AZURE_OPENAI_API_KEY")

    # Claude API configuration
    if not os.getenv("ANTHROPIC_API_KEY"):
        claude_api_key = getpass("Please input your Claude API key: ")
        os.environ["ANTHROPIC_API_KEY"] = claude_api_key

    # Optional: Google Search for research capabilities
    if not os.getenv("GOOGLE_API_KEY"):
        try:
            google_api_key = getpass("Please input your Google API key (optional, press Enter to skip): ")
            if google_api_key:
                os.environ["GOOGLE_API_KEY"] = google_api_key
                search_engine_id = getpass("Please input your Search Engine ID: ")
                if search_engine_id:  # Only set if provided
                    os.environ["SEARCH_ENGINE_ID"] = search_engine_id
                else:
                    print("⚠️ Search Engine ID not provided. Search functionality will be disabled.")
        except KeyboardInterrupt:
            print("Skipping Google Search setup...")

    print("✅ API keys configured!")
ARENAResearchSociety.setup_api_keys = setup_api_keys
```

### What this does:

- Securely collects API credentials using getpass (hidden input)
- Supports Azure OpenAI, Claude (Anthropic), and optional Google Search
- Sets environment variables for seamless integration
- Provides graceful fallbacks for optional components

## 🤖 Azure OpenAI Agent Creation
Create specialized Azure OpenAI agents with custom personas:


```python
def create_azure_agent(self, role_name: str, persona: str, specialization: str) -> ChatAgent:
    """Create an Azure OpenAI agent with specific role and persona"""

    msg_content = textwrap.dedent(f"""
    You are {role_name}, a researcher specializing in AI alignment and safety.

    Your persona: {persona}

    Your specialization: {specialization}

    You are part of a collaborative research team studying the ARENA AI alignment curriculum.
    ARENA focuses on practical AI safety skills including:
    - Mechanistic interpretability
    - Reinforcement learning from human feedback (RLHF)
    - AI governance and policy
    - Robustness and adversarial examples

    When collaborating:
    1. Provide detailed, technical analysis
    2. Reference specific ARENA modules when relevant
    3. Build upon other agents' findings
    4. Maintain academic rigor while being accessible
    5. Always cite sources and provide evidence for claims
    """).strip()

    sys_msg = BaseMessage.make_assistant_message(
        role_name=role_name,
        content=msg_content,
    )

    # Configure Azure OpenAI model with correct API version for o4-mini
    model = AzureOpenAIModel(
        model_type=ModelType.GPT_4O_MINI,
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        url=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_version="2025-01-01-preview",  # Updated to support o4-mini
        azure_deployment_name=os.getenv("AZURE_DEPLOYMENT_NAME") or "div-o4-mini"
    )

    return ChatAgent(
        system_message=sys_msg,
        model=model,
    )
ARENAResearchSociety.create_azure_agent = create_azure_agent
```

### What this does:

- Creates customizable Azure OpenAI agents with specific roles and expertise
- Embeds ARENA curriculum knowledge into each agent's system prompt
- Uses the latest API version compatible with o4-mini model
- Returns a fully configured ChatAgent ready for collaboration

## 🧠 Claude Agent Creation
Create Claude agents with complementary capabilities:


```python
def create_claude_agent(self, role_name: str, persona: str, specialization: str, tools=None) -> ChatAgent:
    """Create a Claude agent with specific role and persona"""

    msg_content = textwrap.dedent(f"""
    You are {role_name}, a researcher specializing in AI alignment and safety.

    Your persona: {persona}

    Your specialization: {specialization}

    You are part of a collaborative research team studying the ARENA AI alignment curriculum.
    ARENA focuses on practical AI safety skills including:
    - Mechanistic interpretability
    - Reinforcement learning from human feedback (RLHF)
    - AI governance and policy
    - Robustness and adversarial examples

    When collaborating:
    1. Provide thorough, nuanced analysis
    2. Consider ethical implications and long-term consequences
    3. Synthesize information from multiple perspectives
    4. Ask probing questions to deepen understanding
    5. Connect concepts across different AI safety domains
    """).strip()  # Remove trailing whitespace

    sys_msg = BaseMessage.make_assistant_message(
        role_name=role_name,
        content=msg_content,
    )

    # Configure Claude model
    model = ModelFactory.create(
        model_platform=ModelPlatformType.ANTHROPIC,
        model_type=ModelType.CLAUDE_3_5_SONNET,
    )

    agent = ChatAgent(
        system_message=sys_msg,
        model=model,
        tools=tools or [],
    )

    return agent
ARENAResearchSociety.create_claude_agent = create_claude_agent
```

### What this does:

- Creates Claude agents with nuanced, philosophical thinking capabilities
- Emphasizes ethical considerations and long-term thinking
- Supports optional tool integration (like search capabilities)
- Uses Claude 3.5 Sonnet for advanced reasoning


## 👥 Workforce Assembly
Bring together all agents into a collaborative workforce:




```python
def create_research_workforce(self):
    """Create the collaborative research workforce"""
    print("🏗️ Creating ARENA Research Society...")

    # Setup search tools for the lead researcher (only if properly configured)
    search_tools = []
    if os.getenv("GOOGLE_API_KEY") and os.getenv("SEARCH_ENGINE_ID"):
        try:
            search_toolkit = SearchToolkit()
            search_tools = [
                FunctionTool(search_toolkit.search_google),
            ]
            print("🔍 Search tools enabled for lead researcher")
        except Exception as e:
            print(f"⚠️ Search tools disabled due to configuration issue: {e}")
            search_tools = []
    else:
        print("🔍 Search tools disabled - missing API keys")

    # Create Claude agents
    claude_lead = self.create_claude_agent(
        role_name="Dr. Claude Alignment",
        persona="A thoughtful, methodical researcher who excels at synthesizing complex information and identifying key insights. Known for asking the right questions and seeing the bigger picture. Works with existing knowledge when search tools are unavailable.",
        specialization="AI safety frameworks, mechanistic interpretability, and curriculum analysis",
        tools=search_tools
    )

    claude_ethicist = self.create_claude_agent(
        role_name="Prof. Claude Ethics",
        persona="A philosophical thinker who deeply considers the ethical implications and long-term consequences of AI development. Bridges technical concepts with societal impact.",
        specialization="AI governance, policy implications, and ethical frameworks in AI alignment"
    )

    # Create Azure OpenAI agents
    azure_technical = self.create_azure_agent(
        role_name="Dr. Azure Technical",
        persona="A detail-oriented technical expert who dives deep into implementation specifics and mathematical foundations. Excellent at breaking down complex algorithms.",
        specialization="RLHF implementation, robustness techniques, and technical deep-dives"
    )

    azure_practical = self.create_azure_agent(
        role_name="Dr. Azure Practical",
        persona="A pragmatic researcher focused on real-world applications and practical implementation. Bridges theory with practice.",
        specialization="Practical AI safety applications, training methodologies, and hands-on exercises"
    )

    # Configure coordinator and task agents to use Azure OpenAI with correct API version
    coordinator_agent_kwargs = {
        'model': AzureOpenAIModel(
            model_type=ModelType.GPT_4O_MINI,
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            url=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version="2025-01-01-preview",
            azure_deployment_name=os.getenv("AZURE_DEPLOYMENT_NAME") or "div-o4-mini"
        ),
        'token_limit': 8000
    }

    task_agent_kwargs = {
        'model': AzureOpenAIModel(
            model_type=ModelType.GPT_4O_MINI,
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            url=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version="2025-01-01-preview",
            azure_deployment_name=os.getenv("AZURE_DEPLOYMENT_NAME") or "div-o4-mini"
        ),
        'token_limit': 16000
    }

    # Create the workforce with proper configuration
    self.workforce = Workforce(
        'ARENA AI Alignment Research Society',
        coordinator_agent_kwargs=coordinator_agent_kwargs,
        task_agent_kwargs=task_agent_kwargs
    )

    # Add agents with descriptive roles
    self.workforce.add_single_agent_worker(
        'Dr. Claude Alignment (Lead Researcher) - Synthesizes information, leads research direction, and provides comprehensive analysis based on existing knowledge',
        worker=claude_lead,
    ).add_single_agent_worker(
        'Prof. Claude Ethics (Ethics & Policy Specialist) - Analyzes ethical implications, policy considerations, and societal impact of AI alignment research',
        worker=claude_ethicist,
    ).add_single_agent_worker(
        'Dr. Azure Technical (Technical Deep-Dive Specialist) - Provides detailed technical analysis, mathematical foundations, and implementation specifics',
        worker=azure_technical,
    ).add_single_agent_worker(
        'Dr. Azure Practical (Applied Research Specialist) - Focuses on practical applications, training methodologies, and hands-on implementation guidance',
        worker=azure_practical,
    )

    print("✅ ARENA Research Society created with 4 specialized agents!")
    return self.workforce
ARENAResearchSociety.create_research_workforce = create_research_workforce
```

### What this does:

- Creates 4 specialized researchers: 2 Claude agents + 2 Azure OpenAI agents
- Each agent has distinct personalities and expertise areas
- Configures search tools for the lead researcher (when available)
- Sets up proper workforce coordination using Azure OpenAI models
- Creates a balanced team covering technical, practical, and ethical perspectives

## 📋 Research Task Creation
Define structured research tasks for the collaborative team:


```python
def create_research_task(self, research_topic: str, specific_questions: str = None) -> Task:
    """Create a research task for the ARENA curriculum"""

    arena_context = {
        "curriculum_info": "ARENA (AI Research and Education Nexus for Alignment) is a comprehensive AI safety curriculum",
        "focus_areas": [
            "Mechanistic Interpretability - Understanding how neural networks work internally",
            "Reinforcement Learning from Human Feedback (RLHF) - Training AI systems to be helpful and harmless",
            "AI Governance - Policy, regulation, and coordination for AI safety",
            "Robustness & Adversarial Examples - Making AI systems robust to attacks and edge cases"
        ],
        "emphasis": "practical skills, hands-on exercises, and real-world applications",
        "website": "https://www.arena.education/curriculum"
    }

    # Check if search tools are available
    has_search = bool(os.getenv("GOOGLE_API_KEY") and os.getenv("SEARCH_ENGINE_ID"))

    base_content = f"""
    Research Topic: {research_topic}

    Please conduct a comprehensive collaborative research analysis on this topic in relation to the ARENA AI alignment curriculum.

    {'Note: Search tools are available for gathering latest information.' if has_search else 'Note: Analysis will be based on existing knowledge as search tools are not available.'}

    Research Process:
    1. **Information Gathering** - {'Collect relevant information about the topic, including latest developments' if has_search else 'Analyze the topic based on existing knowledge and understanding'}
    2. **Technical Analysis** - Provide detailed technical breakdown and mathematical foundations
    3. **Practical Applications** - Explore how this relates to hands-on ARENA exercises and real-world implementation
    4. **Ethical Considerations** - Analyze policy implications and ethical frameworks
    5. **Synthesis** - Combine all perspectives into actionable insights and recommendations

    Expected Deliverables:
    - Comprehensive analysis from each specialist perspective
    - Identification of key concepts and their relationships
    - Practical implementation guidance
    - Policy and ethical considerations
    - Recommendations for further research or curriculum development
    """

    if specific_questions:
        base_content += f"\n\nSpecific Research Questions:\n{specific_questions}"

    return Task(
        content=base_content.strip(),
        additional_info=arena_context,
        id="arena_research_001",
    )
ARENAResearchSociety.create_research_task = create_research_task
```

### What this does:

- Creates structured research tasks with clear objectives and deliverables
- Adapts task content based on available tools (search vs. knowledge-based)
- Includes ARENA curriculum context for focused analysis
- Supports custom research questions for specialized investigations

## 🔬 Research Execution
Execute collaborative research sessions:


```python
def run_research(self, research_topic: str, specific_questions: str = None):
    """Run a collaborative research session"""
    if not self.workforce:
        self.create_research_workforce()

    print(f"🔬 Starting collaborative research on: {research_topic}")
    print("=" * 60)

    task = self.create_research_task(research_topic, specific_questions)
    processed_task = self.workforce.process_task(task)

    print("\n" + "=" * 60)
    print("📊 RESEARCH RESULTS")
    print("=" * 60)
    print(processed_task.result)

    return processed_task.result
ARENAResearchSociety.run_research = run_research
```

## What this does:

- Orchestrates the entire research process
- Creates the workforce if not already initialized
- Processes tasks through the collaborative agent network
- Returns formatted research results


 ## 🎯 Interactive Demo Interface
Create an interactive interface for easy topic selection:


```python
"""Demonstrating the ARENA Research Society"""
society = ARENAResearchSociety()

# Example research topics related to ARENA curriculum
sample_topics = {
        1: {
            "topic": "Mechanistic Interpretability in Large Language Models",
            "questions": """
            - How do the latest mechanistic interpretability techniques apply to understanding LLM behavior?
            - What are the most effective methods for interpreting attention patterns and residual streams?
            - How can mechanistic interpretability inform AI alignment strategies?
            - What are the current limitations and future directions in this field?
            """
        },
        2: {
            "topic": "RLHF Implementation Challenges and Best Practices",
            "questions": """
            - What are the main technical challenges in implementing RLHF at scale?
            - How do different reward modeling approaches compare in effectiveness?
            - What are the alignment implications of various RLHF techniques?
            - How can we address issues like reward hacking and distributional shift?
            """
        },
        3: {
            "topic": "AI Governance Frameworks for Emerging Technologies",
            "questions": """
            - What governance frameworks are most suitable for rapidly advancing AI capabilities?
            - How can policy makers balance innovation with safety considerations?
            - What role should technical AI safety research play in policy development?
            - How can international coordination on AI governance be improved?
            """
        }
    }

print("🎯 ARENA AI Alignment Research Society")
print("Choose a research topic or provide your own:")
print()

for num, info in sample_topics.items():
        print(f"{num}. {info['topic']}")
print("4. Custom research topic")
print()

try:
      choice = input("Enter your choice (1-4): ").strip()

      if choice in ['1', '2', '3']:
            topic_info = sample_topics[int(choice)]
            result = society.run_research(
                topic_info["topic"],
                topic_info["questions"]
            )
      elif choice == '4':
            custom_topic = input("Enter your research topic: ").strip()
            custom_questions = input("Enter specific questions (optional): ").strip()
            result = society.run_research(
                custom_topic,
                custom_questions if custom_questions else None
            )
      else:
            print("Invalid choice. Running default research...")
            result = society.run_research(sample_topics[1]["topic"], sample_topics[1]["questions"])

except KeyboardInterrupt:
        print("\n👋 Research session interrupted.")
except Exception as e:
        print(f"❌ Error during research: {e}")


```

## What this does:

- Provides pre-defined research topics relevant to ARENA curriculum
- Offers custom topic input for flexible research
- Handles user interaction gracefully with error handling
- Demonstrates the full capabilities of the collaborative AI society

## 🚀 Running the Cookbook
To run this collaborative AI research society:


Execute Individual cells.

Follow prompts: Enter your API credentials and select research topics

The system will create a collaborative research environment where Claude and Azure OpenAI agents work together to produce comprehensive analysis on AI alignment topics!

## 🎯 Conclusion
The future of AI collaboration is here, and this CAMEL-powered society demonstrates the incredible potential of multi-agent systems working across different AI platforms.

In this cookbook, you've learned how to:

- Build cross-platform AI collaboration between Claude 4 and Azure OpenAI models
- Create specialized AI researchers with distinct personas and expertise areas
- Implement robust workforce management using CAMEL's advanced orchestration
- Handle complex API configurations for multiple AI providers seamlessly
- Design structured research workflows for AI alignment and safety topics
- Create scalable agent societies that can tackle complex, multi-faceted problems

This collaborative approach showcases how different AI models can complement each other - Claude's nuanced reasoning and ethical considerations paired with Azure OpenAI's technical precision creates a powerful research dynamic. The ARENA AI alignment focus demonstrates how these societies can be specialized for cutting-edge domains like mechanistic interpretability, RLHF, and AI governance.

As the field of multi-agent AI systems continues to evolve, frameworks like CAMEL are paving the way for increasingly sophisticated collaborations. Whether you're researching AI safety, exploring complex technical topics, or building specialized knowledge teams, the patterns and techniques in this cookbook provide a solid foundation for the next generation of AI-powered research.

The possibilities are endless when AI agents work together. Keep experimenting, keep collaborating, and keep pushing the boundaries of what's possible.

Happy researching! 🔬✨





That's everything: Got questions about 🐫 CAMEL-AI? Join us on [Discord](https://discord.camel-ai.org)! Whether you want to share feedback, explore the latest in multi-agent systems, get support, or connect with others on exciting projects, we’d love to have you in the community! 🤝

Check out some of our other work:

1. 🐫 Creating Your First CAMEL Agent [free Colab](https://docs.camel-ai.org/cookbooks/create_your_first_agent.html)

2.  Graph RAG Cookbook [free Colab](https://colab.research.google.com/drive/1uZKQSuu0qW6ukkuSv9TukLB9bVaS1H0U?usp=sharing)

3. 🧑‍⚖️ Create A Hackathon Judge Committee with Workforce [free Colab](https://colab.research.google.com/drive/18ajYUMfwDx3WyrjHow3EvUMpKQDcrLtr?usp=sharing)

4. 🔥 3 ways to ingest data from websites with Firecrawl & CAMEL [free Colab](https://colab.research.google.com/drive/1lOmM3VmgR1hLwDKdeLGFve_75RFW0R9I?usp=sharing)

5. 🦥 Agentic SFT Data Generation with CAMEL and Mistral Models, Fine-Tuned with Unsloth [free Colab](https://colab.research.google.com/drive/1lYgArBw7ARVPSpdwgKLYnp_NEXiNDOd-?usp=sharingg)

Thanks from everyone at 🐫 CAMEL-AI


<div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: "1rem", marginBottom: "2rem" }}>
  <a href="https://www.camel-ai.org/">
    <img src="https://i.postimg.cc/KzQ5rfBC/button.png" width="150" alt="CAMEL Homepage"/>
  </a>
  <a href="https://discord.camel-ai.org">
    <img src="https://i.postimg.cc/L4wPdG9N/join-2.png" width="150" alt="Join Discord"/>
  </a>
</div>  

⭐ *Star us on [GitHub](https://github.com/camel-ai/camel), join our [Discord](https://discord.camel-ai.org), or follow us on [X](https://x.com/camelaiorg)*

---

