# 🧠 CAMEL Multi-Agent Research Assistant

A powerful, AI-driven research assistant built using the [CAMEL-AI](https://www.camel-ai.org/) framework. This application leverages multiple specialized toolkits and a role-playing agent architecture to autonomously generate comprehensive research reports on any given topic.

## 🚀 Features

- **Multi-Agent Collaboration**: Utilizes CAMEL's role-playing framework to simulate interactions between a "Project Manager" and a "Researcher Agent" for dynamic task execution.
- **Diverse Toolkit Integration**: Incorporates various CAMEL toolkits including:
  - `GoogleScholarToolkit` and `SemanticScholarToolkit` for academic paper retrieval.
  - `ArxivToolkit` for accessing preprints.
  - `AskNewsToolkit` for fetching relevant news articles.
  - `ThinkingToolkit` for planning and synthesis.
  - `FileWriteToolkit` for saving reports locally.
  - `LinkedInToolkit` for potential dissemination.
  - `OpenAIImageToolkit` for generating illustrative images.
- **Streamlit Interface**: Provides an intuitive web interface for users to input topics and receive generated reports.

## 🛠️ Installation

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/camel-ai/camel.git
   cd camel/examples/usecases/multi_agent_research_assistant
   ```

2. **Create and Activate a Virtual Environment**:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. ## 🛠️ Setup Environment Variables

   Copy the provided `.env.template` to `.env`:

   Open the `.env` file in your preferred editor and add your required API keys. At a minimum, you need to provide your OpenAI API key:

   ```env
   OPENAI_API_KEY=your_openai_api_key
   ```

   Replace `your_openai_api_key` with your actual key from OpenAI.

   Additional environment variables may be required depending on the toolkits you enable (e.g., for LinkedIn, DALL·E, news APIs, etc.).


## ▶️ Running the Application

Start the Streamlit application:

```bash
streamlit run app.py
```

This will open the application in your default web browser. Enter a research topic and click "Generate Report" to initiate the multi-agent research process.

## 📂 Project Structure

```
camel-research-assistant/
├── app.py               # Main Streamlit application
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (not included in version control)
└── README.md            # Project documentation
```

## 🧪 Example Usage

1. Launch the application.
2. Input a topic, e.g., "Latest breakthroughs in quantum computing".
3. Click "Generate Report".
4. The application will:
   - Identify top researchers in the field.
   - Retrieve relevant academic papers and news articles.
   - Generate a comprehensive report.
   - Save the report locally.
   - Optionally, generate illustrative images and prepare content for LinkedIn dissemination.