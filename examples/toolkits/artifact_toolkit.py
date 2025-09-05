from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import ArtifactToolkit
from camel.types import ModelPlatformType
from camel.types.enums import ModelType

# Create a model instance
model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)

# Define system message for the agent
sys_msg = """You are a creative assistant that specializes in generating visual artifacts.
You can create HTML documents, SVG graphics, Mermaid flowcharts, code snippets with syntax highlighting,
Markdown documents, and LaTeX mathematical expressions. When creating artifacts, make them visually
appealing and informative. Always use the appropriate artifact creation method for the content type."""


# Initialize the ArtifactToolkit
artifact_toolkit = ArtifactToolkit()

# Get the tools from the toolkit
tools_list = artifact_toolkit.get_tools()

# Initialize a ChatAgent with the tools
camel_agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=tools_list,
)

print("=" * 60)

# Example 1: Create an HTML artifact
html_query = """Create an interactive HTML page that demonstrates a simple calculator.
Include a modern design with CSS styling, input fields for numbers, and buttons for
basic operations (+, -, *, /). Make it visually appealing with a clean interface."""

camel_agent.reset()
response = camel_agent.step(html_query)
print("Example 1: Creating an HTML Calculator")
print(response.msgs[0].content)
print("Tool calls:", response.info['tool_calls'])
print("\n")
"""
I've created an interactive, modern-styled HTML calculator page. It includes:

- Two numeric input fields (Value A and Value B)
- Buttons for +, -, x, ÷ and a Compute button
- A visual keypad for entering numbers
- Result display with formatted output and the equation shown
- History of recent calculations (click a history item to load it)
- Swap, Clear, Copy, and Clear History controls
- Keyboard support (Enter to compute, + - * / to choose operations)
- Responsive, attractive CSS design

You can copy the provided HTML and save it as a .html file (for example, calculator.html) and open it in any modern browser. If you'd like any changes - different colors, additional operations (percent, power), keyboard-only mode, or accessibility tweaks - tell me which ones and I'll update it.
Tool calls: [ToolCallingRecord(tool_name='create_html_artifact', args={'content': '<!doctype html>\n<html lang="en">\n<head>\n  <meta charset="utf-8" />\n  <meta name="viewport" content="width=device-width,initial-scale=1" />\n  <title>Modern Simple Calculator</title>\n  <style>\n    :root{\n      --bg:#0f1724;        /* deep navy */\n      --card:#0b1220;\n      --muted:#94a3b8;\n      --accent:#7c5cff;     /* purple */\n      --accent-2:#00d4ff;   /* cyan */\n      --glass: rgba(255,255,255,0.04);\n      --success: #22c55e;\n      --danger: #ff6b6b;\n      --glass-border: rgba(255,255,255,0.06);\n      font-family: Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial;\n    }\n    *{box-sizing:border-box}\n    html,body{height:100%}\n    body{\n      margin:0;\n      background: radial-gradient(1200px 600px at 10% 10%, rgba(124,92,255,0.12), transparent 6%),\n                  radial-gradient(900px 420px at 90% 90%, rgba(0,212,255,0.06), transparent 6%),\n                  linear-gradient(180deg,var(--bg), #07101a 60%);\n      color:#e6eef8;\n      display:flex;align-items:center;justify-content:center;\n      padding:32px;\n    }\n\n    .calculator{\n      width: 100%;\n      max-width: 860px;\n      background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));\n      border-radius:16px;\n      padding:22px;\n      box-shadow: 0 10px 30px rgba(2,6,23,0.6);\n      border: 1px solid var(--glass-border);\n      display:grid;\n      grid-template-columns: 1fr 380px;\n      gap:18px;\n    }\n\n    /* Left pane: controls */\
"""

# Example 2: Create an SVG artifact
svg_query = """Generate an SVG graphic that shows a data visualization - a simple bar chart
representing monthly sales data for a fictional company. Include 6 bars for different months,
use different colors for each bar, and add labels for the months and values."""

camel_agent.reset()
response = camel_agent.step(svg_query)
print("Example 2: Creating an SVG Bar Chart")
print(response.msgs[0].content)
print("Tool calls:", response.info['tool_calls'])
print("\n")

"""
Example 2: Creating an SVG Bar Chart
I've created the SVG bar chart. You can copy the SVG below and save it as a .svg file or embed it directly in HTML.

(If you want different months, values, colors, or a downloadable PNG/PNG export, tell me and I can update it.)

Here's the SVG:

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 400" role="img" aria-labelledby="title desc">
  <title id="title">Monthly Sales - Fictional Company</title>
  <desc id="desc">A bar chart showing sales for six months (Jan-Jun). Each bar is a different color and labeled with its value. Y-axis shows scale up to 240.</desc>
  <defs>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#000" flood-opacity="0.15"/>
    </filter>
    <linearGradient id="grad" x1="0" x2="0" y1="0" y2="1">
      <stop offset="0%" stop-color="#ffffff" stop-opacity="0.06"/>
      <stop offset="100%" stop-color="#000000" stop-opacity="0.02"/>
    </linearGradient>
  </defs>

  <!-- Chart area background -->
  <rect x="50" y="40" width="700" height="300" rx="8" fill="#fbfbfb" stroke="#eee" />

  <!-- Title -->
  <text x="400" y="28" text-anchor="middle" font-family="Segoe UI, Roboto, Arial" font-size="18" fill="#333" font-weight="600">Monthly Sales (Jan-Jun)</text>

  <!-- Y axis gridlines & labels -->
  <g font-family="Segoe UI, Roboto, Arial" font-size="12" fill="#666">
    <!-- ticks: 240,200,150,100,50,0 -->
    <line x1="60" x2="740" y1="50" y2="50" stroke="#eee"/>
    <text x="48" y="54" text-anchor="end">240</text>

    <line x1="60" x2="740" y1="98.3333" y2="98.3333" stroke="#f5f5f5"/>
    <text x="48" y="102.3333" text-anchor="end">200</text>

    <line x1="60" x2="740" y1="158.75" y2="158.75" stroke="#f5f5f5"/>
    <text x="48" y="162.75" text-anchor="end">150</text>

    <line x1="60" x2="740" y1="219.1667" y2="219.1667" stroke="#f5f5f5"/>
    <text x="48" y="223.1667" text-anchor="end">100</text>

    <line x1="60" x2="740" y1="279.5833" y2="279.5833" stroke="#f5f5f5"/>
    <text x="48" y="283.5833" text-anchor="end">50</text>

    <line x1="60" x2="740" y1="340" y2="340" stroke="#ddd"/>
    <text x="48" y="344" text-anchor="end">0</text>
  </g>

  <!-- X axis line -->
  <line x1="60" x2="740" y1="340" y2="340" stroke="#333" stroke-opacity="0.08"/>

  <!-- Bars -->
  <g filter="url(#shadow)">
    <!-- Data: [120,200,150,80,220,170] -->
    <rect x="80"  y="195" width="93.3333" height="145" rx="6" fill="#4E79A7" />
    <rect x="193.3333" y="98.3333" width="93.3333" height="241.6667" rx="6" fill="#FF9F40" />
    <rect x="306.6667" y="158.75" width="93.3333" height="181.25" rx="6" fill="#59A14F" />
    <rect x="420" y="243.3333" width="93.3333" height="96.6667" rx="6" fill="#B07AA1" />
    <rect x="533.3333" y="74.1667" width="93.3333" height="265.8333" rx="6" fill="#FF595E" />
    <rect x="646.6667" y="134.5833" width="93.3333" height="205.4167" rx="6" fill="#2ECEC8" />

    <!-- subtle gradient overlay for polish -->
    <rect x="80"  y="195" width="93.3333" height="145" rx="6" fill="url(#grad)" opacity="0.12" />
    <rect x="193.3333" y="98.3333" width="93.3333" height="241.6667" rx="6" fill="url(#grad)" opacity="0.12" />
    <rect x="306.6667" y="158.75" width="93.3333" height="181.25" rx="6" fill="url(#grad)" opacity="0.12" />
    <rect x="420" y="243.3333" width="93.3333" height="96.6667" rx="6" fill="url(#grad)" opacity="0.12" />
    <rect x="533.3333" y="74.1667" width="93.3333" height="265.8333" rx="6" fill="url(#grad)" opacity="0.12" />
    <rect x="646.6667" y="134.5833" width="93.3333" height="205.4167" rx="6" fill="url(#grad)" opacity="0.12" />
  </g>

  <!-- Value labels above bars -->
  <g font-family="Segoe UI, Roboto, Arial" font-size="12" fill="#222" font-weight="600">
    <text x="126.6667" y="186" text-anchor="middle">120</text>
    <text x="240" y="88" text-anchor="middle">200</text>
    <text x="353.3333" y="150" text-anchor="middle">150</text>
    <text x="466.6667" y="236" text-anchor="middle">80</text>
    <text x="586.6667" y="66" text-anchor="middle">220</text>
    <text x="693.3333" y="126" text-anchor="middle">170</text>
  </g>

  <!-- Month labels -->
  <g font-family="Segoe UI, Roboto, Arial" font-size="13" fill="#333">
    <text x="126.6667" y="360" text-anchor="middle">Jan</text>
    <text x="240" y="360" text-anchor="middle">Feb</text>
    <text x="353.3333" y="360" text-anchor="middle">Mar</text>
    <text x="466.6667" y="360" text-anchor="middle">Apr</text>
    <text x="586.6667" y="360" text-anchor="middle">May</text>
    <text x="693.3333" y="360" text-anchor="middle">Jun</text>
  </g>

  <!-- Legend / footnote -->
  <text x="60" y="382" font-family="Segoe UI, Roboto, Arial" font-size="11" fill="#666">Sales (units)</text>

</svg>
Tool calls: [ToolCallingRecord(tool_name='create_svg_artifact', args={'svg_content': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 400" role="img" aria-labelledby="title desc">\n  <title id="title">Monthly Sales - Fictional Company</title>\n  <desc id="desc">A bar chart showing sales for six months (Jan-Jun). Each bar is a different color and labeled with its value. Y-axis shows scale up to 240.</desc>\n  <defs>\n    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">\n      <feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#000" flood-opacity="0.15"/>\n    </filter>\n    <linearGradient id="grad" x1="0" x2="0" y1="0" y2="1">\n      <stop offset="0%" stop-color="#ffffff" stop-opacity="0.06"/>\n      <stop offset="100%" stop-color="#000000" stop-opacity="0.02"/>\n    </linearGradient>\n  </defs>\n\n  <!
"""

# Example 3: Create a Mermaid flowchart
mermaid_query = """Create a Mermaid flowchart that shows the decision-making process for
choosing a programming language for a new project. Include decision points for factors like
project type (web, mobile, desktop), team experience, performance requirements, and budget."""

camel_agent.reset()
response = camel_agent.step(mermaid_query)
print("Example 3: Creating a Mermaid Decision Flowchart")
print(response.msgs[0].content)
print("Tool calls:", response.info['tool_calls'])
print("\n")
"""
Example 3: Creating a Mermaid Decision Flowchart
I've created the Mermaid flowchart. If you want, I can:
- Export it as an SVG or PNG,
- Adjust wording, add more decision nodes (e.g., library ecosystem, platform constraints, deployment targets),
- Produce a simplified text-only ASCII flowchart or a downloadable HTML page.

Which would you like next?
Tool calls: [ToolCallingRecord(tool_name='create_mermaid_flowchart', args={'flowchart_definition': 'flowchart TD\n  Start([Start: Choosing a programming language])\n  PT{Project type?}\n  Start --> PT\n  PT -->|Web| Web\n  PT -->|Mobile| Mobile\n  PT -->|Desktop| Desktop\n\n  Web --> TE[Team experience with relevant tech?]\n  Mobile --> TE\n  Desktop --> TE\n\n  TE -->|Yes: Familiar stack| PreferF[Prefer familiar language for faster delivery]\n  TE -->|No: Team open to learning| NewLang[Open to new language; evaluate trade-offs]\n\n  PreferF --> PR{Performance requirements?}\n  NewLang --> PR\n\n  PR -->|High (near-metal, real-time)| PerfHigh[Consider: C, C++, Rust, Go]\n  PR -->|Moderate (server, concurrency)| PerfMod[Consider: Java, C#, Go, Rust]\n  PR -->|Low (rapid dev, scripting)| PerfLow[Consider: Python, Ruby, JavaScript/TypeScript]\n\n  PerfHigh --> BUD{Budget?}\n  PerfMod --> BUD\n  PerfLow --> BUD\n\n  BUD -->|Low| BudgetLow[Favor open-source ecosystems: Node.js, Python, Go, Rust]\n  BUD -->|High| BudgetHigh[Can choose commercial/enterprise stacks: Java/.NET, native mobile (Swift/Kotlin)]\n\n  BudgetLow --> RECS[Recommendations by project type:\\n- Web: JS/TS (React + Node), Python (Django/Flask), Go\\n- Mobile: React Native, Flutter (cross), or Kotlin/Swift (native)\\n- Desktop: Electron, Qt, .NET, 
"""
# Example 4: Create a code artifact
code_query = """Generate a Python code snippet that implements a simple machine learning
model using scikit-learn. Include data preprocessing, model training, and evaluation.
Make sure to include proper comments and use a real dataset example."""

camel_agent.reset()
response = camel_agent.step(code_query)
print("Example 4: Creating a Python ML Code Artifact")
print(response.msgs[0].content)
print("Tool calls:", response.info['tool_calls'])
print("\n")

"""
Example 4: Creating a Python ML Code Artifact
Here's a ready-to-run Python snippet that uses scikit-learn to build, train, and evaluate a simple ML model on the Iris dataset. It includes preprocessing, cross-validation, evaluation metrics, and a confusion matrix plot.

If you'd like a different model (e.g., RandomForest, SVM) or dataset (e.g., Wine, Breast Cancer, CSV file), tell me and I can modify it.

(You can copy the code from the code artifact titled "Iris classification with scikit-learn".)
Tool calls: [ToolCallingRecord(tool_name='create_code_artifact', args={'code': '
"""

# Example 5: Create a Markdown document
markdown_query = """Create a comprehensive Markdown document that explains the concept of
artificial intelligence, including its history, types (narrow AI, general AI, super AI),
applications, and future prospects. Include headings, bullet points, code examples,
and a table comparing different AI approaches."""

camel_agent.reset()
response = camel_agent.step(markdown_query)
print("Example 5: Creating a Markdown AI Guide")
print(response.msgs[0].content)
print("Tool calls:", response.info['tool_calls'])
print("\n")

"""
Example 5: Creating a Markdown AI Guide
I've created a comprehensive Markdown document on artificial intelligence that includes headings, a table of contents, history, types (narrow, general, super), major approaches, a comparison table, applications, code examples, challenges, future prospects, ethics, and further resources.

You can view or download the document titled "Artificial Intelligence - Overview". If you'd like any changes - for example, expanded sections, additional code notebooks, slides, or an infographic - tell me which parts you'd like expanded or converted and I'll produce them.
Tool calls: [ToolCallingRecord(tool_name='create_markdown_artifact', args={'markdown_content': '# Artificial Intelligence — A Comprehensive Overview\n\n## Table of contents\n\n- [What is Artificial Intelligence?](#what-is-artificial-intelligence)\n- [Brief History of AI](#brief-history-of-ai)\n- [Types of AI](#types-of-ai)\n  - [Narrow (Weak) AI](#narrow-weak-ai)\n  - [General (Strong) AI](#general-strong-ai)\n  - [Superintelligence (Super AI)](#superintelligence-super-ai)\n- [Major AI Approaches](#major-ai-approaches)\n- [Comparison Table: AI Approaches](#comparison-table-ai-approaches)\n- [Common Applications of AI](#common-applications-of-ai)\n- [Code Examples](#code-examples)\n  - [1) Rule-based / Symbolic Example (Python)](#1-rule-based--symbolic-example-python)\n  - [2) Classical Machine Learning (scikit-learn)](#2-classical-machine-learning-scikit-learn)\n  - [3) Deep Learning (PyTorch minimal example)](#3-deep-learning-pytorch-minimal-example)\n  - [4) Using a Pretrained Transformer (Hugging Face)](#4-using-a-pretrained-transformer-hugging-face)\n- [Challenges and Risks](#challenges-and-risks)\n- [Future Prospects](#future-prospects)\n- [Ethics, Governance, and Safety](#ethics-governance-and-safety)\n- [Further Reading & Resources](#further-reading--resources)\n\n---\n\n## What is Artificial Intelligence?\n\nArtificial Intelligence (AI) is the field of computer science focused on creating systems that perform tasks that normally require human intelligence. These tasks include reasoning, learning, perception, planning, language understanding, and problem-solving.\n\nKey ideas:\n\n- AI systems can be rule-based (explicit programming) or data-driven (learning from examples).\n- AI is interdisciplinary: it draws from computer science, statistics, cognitive science, neuroscience, and more.\n\
"""

# Example 6: Create a LaTeX math artifact
latex_query = """Generate a LaTeX mathematical expression that demonstrates a complex
mathematical concept, such as the Fourier Transform or the Schrödinger equation.
Include the equation in display mode and provide a brief explanation of what it represents."""

camel_agent.reset()
response = camel_agent.step(latex_query)
print("Example 6: Creating a LaTeX Mathematical Expression")
print(response.msgs[0].content)
print("Tool calls:", response.info['tool_calls'])
print("\n")

"""
Example 6: Creating a LaTeX Mathematical Expression
Here's a display-mode LaTeX expression for the time-dependent Schrödinger equation, with a brief explanation:

\[
\begin{aligned}
i\hbar\,\frac{\partial}{\partial t}\,\psi(\mathbf{x},t) &=\left[ -\frac{\hbar^{2}}{2m}\,\nabla^{2} + V(\mathbf{x},t) \right]\,\psi(\mathbf{x},t), \\
\psi(\mathbf{x},t) &= \hat{U}(t,t_0)\,\psi(\mathbf{x},t_0), \qquad
\hat{U}(t,t_0) = \mathcal{T}\exp\left(-\frac{i}{\hbar}\int_{t_0}^{t} \hat{H}(t')\,dt'\right),
\end{aligned}
\]

Explanation:
- The first line is the time-dependent Schrödinger equation: it governs the quantum time evolution of the wavefunction ψ(x,t) for a particle of mass m under potential V(x,t). Here ħ is the reduced Planck constant and ∇² is the Laplacian (spatial second derivatives).
- The second line expresses the solution formally via a time-evolution operator U(t,t0). The operator is given by the time-ordered exponential of the Hamiltonian Ĥ(t'), which accounts for possibly time-dependent Hamiltonians; T denotes time-ordering. This operator evolves the state from initial time t0 to time t.
Tool calls: [ToolCallingRecord(tool_name='create_latex_math', args={'latex_expression': "\\begin{aligned}\ni\\hbar\\,\\frac{\\partial}{\\partial t}\\,\\psi(\\mathbf{x},t) &=\\left[ -\\frac{\\hbar^{2}}{2m}\\,\\nabla^{2} + V(\\mathbf{x},t) \\right]\\,\\psi(\\mathbf{x},t), \\\\\n\\psi(\\mathbf{x},t) &= \\hat{U}(t,t_0)\\,\\psi(\\mathbf{x},t_0), \\qquad\n\\hat{U}(t,t_0) = \\mathcal{T}\\exp\\left(-\\frac{i}{\\hbar}\\int_{t_0}^{t} \\hat{H}(t')\\,dt'\\right),\n\\end{aligned}", 'title': 'Time-Dependent Schrödinger Equation', 'display_mode': 'block', 'show_source': False}, result={'type': 'latex', 'subtype': 'math', 'title': 'Time-Dependent Schrödinger Equation', 'content': '<!DOCTYPE html>\n<html lang="en">\n<head>\n    <meta charset="UTF-8">\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n    <title>Time-Dependent Schrödinger Equation</title>\n    <style>\n        body {\n            font-family: \'Segoe UI\', Tahoma, Geneva, Verdana, sans-serif;\n            line-height: 1.6;\n            color: #333;\n            margin: 0 auto;\n            padding: 20px;\n            background-color: #f9f9f9;\n        }\n        h1, h2, h3, h4, h5, h6 { \n            color: #2c3e50; \n            margin-top: 0;\n        }\n        .container {\n            background: white;\n            p
"""
