# AI Project Planning Team 🚀

An intelligent project planning tool powered by Mistral AI and CAMEL-AI that helps teams create detailed technical architecture and project timelines. This Streamlit application leverages CAMEL-AI framework to provide expert-level project planning assistance.

## 🌟 Features

- **Technical Architecture Design**: Get AI-powered recommendations for system architecture, technologies, and frameworks
- **Project Timeline Planning**: Generate detailed project timelines with phases, milestones, and deadlines
- **Interactive Editing**: Modify and customize both architecture and timeline plans
- **PDF Export**: Download your project plan as a professionally formatted PDF
- **User-Friendly Interface**: Clean and intuitive Streamlit-based UI

## 🛠️ Prerequisites

- Python 3.10+
- Mistral AI API key (Get it from [Mistral AI Console](https://console.mistral.ai/home))

## 📦 Installation

1. **Clone the Repository**:

```bash
git clone https://github.com/camel-ai/camel.git
cd camel/examples/usecases/mistral_project_planner
```

2. **Create and Activate a Virtual Environment**:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install the required dependencies**:

```bash
pip install -r requirements.txt
```

## 🔧 Required Dependencies

- streamlit
- xhtml2pdf
- jinja2
- markdown
- camel-ai

## 🚀 Usage

1. Start the application:

```bash
streamlit run app.py
```

2. Open your web browser and navigate to the provided local URL (typically http://localhost:8501)

3. Enter your Mistral AI API key in the sidebar

4. Fill in the project details:

   - Project Name
   - Project Description
   - Project Type
   - Preferred Technologies
   - Team Size
   - Start Date

5. Click "Generate Project Plan" to create your project plan

6. Review, edit, and download your project plan as needed

## 📋 Project Information Input

The application accepts the following project details:

- **Project Types**: Web Application, Mobile App, Desktop Application, API Service, Data Pipeline, Other
- **Technologies**: Python, JavaScript, Java, C#, Go, Ruby, PHP, React, Angular, Vue.js, Node.js, Django, Flask, Spring, .NET, Docker, Kubernetes, AWS, Azure, GCP
- **Team Size**: 1-20 members
- **Start Date**: Custom date selection

## 📄 Output

The application generates:

1. Technical Architecture document
2. Detailed Project Timeline
3. Exportable PDF containing all project information

- Built with [CAMEL-AI](https://github.com/camel-ai/camel)
- Powered by [Mistral AI](https://mistral.ai/)
- UI Framework: [Streamlit](https://streamlit.io/)

## 📧 Support

For support, please open an issue in the repository or contact the maintainers.
