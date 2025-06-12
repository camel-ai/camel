import os
import io
import streamlit as st
from datetime import datetime
from xhtml2pdf import pisa
from jinja2 import Template
import markdown

from camel.configs import MistralConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.agents import ChatAgent

# ─── STEP 1: set_page_config MUST be the first Streamlit call ───
st.set_page_config(
    page_title="AI Project Planning Team 🚀",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── STEP 2: Initialize all session_state keys before reading them ───
if 'generated' not in st.session_state:
    st.session_state.generated = False
if 'architecture' not in st.session_state:
    st.session_state.architecture = ""
if 'timeline' not in st.session_state:
    st.session_state.timeline = ""
if 'project_name' not in st.session_state:
    st.session_state.project_name = ""
if 'project_type' not in st.session_state:
    st.session_state.project_type = ""
if 'team_size' not in st.session_state:
    st.session_state.team_size = 3
if 'start_date' not in st.session_state:
    st.session_state.start_date = datetime.now()
if 'technologies' not in st.session_state:
    st.session_state.technologies = []
if 'description' not in st.session_state:
    st.session_state.description = ""

# ─── STEP 3: Sidebar Inputs (safe to read from session_state now) ───
st.sidebar.header("⚙️ Configuration")
api_key = st.sidebar.text_input(
    "Mistral API Key", type="password", help="Get it from https://console.mistral.ai/home"
)
if api_key:
    os.environ["MISTRAL_API_KEY"] = api_key

st.sidebar.markdown("---")
st.sidebar.header("📝 Project Information")

project_name = st.sidebar.text_input("Project Name", value=st.session_state.project_name)
project_description = st.sidebar.text_area("Project Description", value=st.session_state.description)
project_type = st.sidebar.selectbox(
    "Project Type",
    ["Web Application", "Mobile App", "Desktop Application", "API Service", "Data Pipeline", "Other"],
    index=(["Web Application", "Mobile App", "Desktop Application", "API Service", "Data Pipeline", "Other"]
           .index(st.session_state.project_type)
           if st.session_state.project_type else 0)
)
tech_stack = st.sidebar.multiselect(
    "Preferred Technologies (Optional)",
    ["Python", "JavaScript", "Java", "C#", "Go", "Ruby", "PHP", "React", "Angular", "Vue.js",
     "Node.js", "Django", "Flask", "Spring", ".NET", "Docker", "Kubernetes", "AWS", "Azure", "GCP"],
    default=st.session_state.technologies
)
team_size = st.sidebar.number_input(
    "Team Size", min_value=1, max_value=20, value=st.session_state.team_size
)
start_date = st.sidebar.date_input("Project Start Date", value=st.session_state.start_date)

# ─── STEP 4: Main UI Components ───
st.title("AI Project Planning Team 🚀")
st.markdown("Get expert technical architecture and project timeline planning for your project.")

def generate_pdf():
    # Build an HTML template with an explicit <table> for the timeline
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 40px;
                line-height: 1.6;
            }
            h1, h2, h3 {
                margin-top: 20px;
                margin-bottom: 10px;
            }
            p {
                margin: 10px 0;
            }
            /* Table styling for xhtml2pdf */
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
                margin-bottom: 20px;
            }
            th, td {
                border: 1px solid #333;
                padding: 6px;
                text-align: left;
                font-size: 12px;
            }
            th {
                background-color: #f2f2f2;
            }
            ul, ol {
                margin: 10px 0;
                padding-left: 20px;
            }
            li {
                margin: 5px 0;
            }
        </style>
    </head>
    <body>
        <h1>Project Plan: {{ project_name }}</h1>
        
        <h2>Project Information</h2>
        <p><strong>Project Type:</strong> {{ project_type }}</p>
        <p><strong>Team Size:</strong> {{ team_size }}</p>
        <p><strong>Start Date:</strong> {{ start_date }}</p>
        <p><strong>Technologies:</strong> {{ technologies }}</p>
        <p><strong>Description:</strong> {{ description }}</p>

        <h2>Technical Architecture</h2>
        {{ architecture_html | safe }}

        <h2>Project Timeline</h2>
        {{ timeline_html | safe }}

        <p><em>Generated on: {{ generated_date }}</em></p>
    </body>
    </html>
    """

    # Convert the Markdown‐formatted architecture into safe HTML
    architecture_html = markdown.markdown(st.session_state.architecture)

    # Convert the timeline content to HTML
    # First try to convert as markdown (which will handle tables if they exist)
    timeline_html = markdown.markdown(st.session_state.timeline)

    # Render the Jinja2 template with the HTML pieces
    template = Template(html_template)
    html_content = template.render(
        project_name=st.session_state.project_name,
        project_type=st.session_state.project_type,
        team_size=st.session_state.team_size,
        start_date=st.session_state.start_date,
        technologies=', '.join(st.session_state.technologies) if st.session_state.technologies else 'Not specified',
        description=st.session_state.description,
        architecture_html=architecture_html,
        timeline_html=timeline_html,
        generated_date=datetime.now().strftime("%Y-%m-%d %H:%M")
    )

    # Convert the HTML to PDF bytes via xhtml2pdf
    output_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(src=html_content, dest=output_buffer)
    if pisa_status.err:
        st.error("Error generating PDF. Check your HTML for invalid CSS or table markup.")
        return None

    return output_buffer.getvalue()


# ─── STEP 5: Trigger agents & store responses ───
if st.sidebar.button("Generate Project Plan"):
    if not api_key:
        st.error("Please enter your Mistral API key first.")
    elif not project_name or not project_description:
        st.error("Please provide both project name and description.")
    else:
        # Create the Mistral model instance
        mistral_model = ModelFactory.create(
            model_platform=ModelPlatformType.MISTRAL,
            model_type=ModelType.MISTRAL_LARGE,
            model_config_dict=MistralConfig(temperature=0.0).as_dict(),
        )

        project_context = f"""
        Project Name: {project_name}
        Project Type: {project_type}
        Team Size: {team_size}
        Start Date: {start_date}
        Preferred Technologies: {', '.join(tech_stack) if tech_stack else 'Not specified'}
        
        Project Description:
        {project_description}
        """

        # 1) Technical Architect
        with st.spinner("Technical Architect is designing the system..."):
            architect = ChatAgent(
                system_message=(
                    "You are a Technical Architect. Your role is to:\n"
                    "1. Design a scalable and maintainable system architecture\n"
                    "2. Recommend appropriate technologies and frameworks\n"
                    "3. Define key components and their interactions\n"
                    "4. Consider security, scalability, and performance\n"
                    "Be specific and practical in your recommendations."
                ),
                message_window_size=10,
                model=mistral_model,
            )
            arch_resp = architect.step(
                f"Design the technical architecture for this project:\n\n{project_context}"
            )
            st.session_state.architecture = arch_resp.msgs[0].content

        # 2) Project Timeline Planner
        with st.spinner("Project Timeline Planner is creating the schedule..."):
            planner = ChatAgent(
                system_message=(
                    "You are a Project Timeline Planner. Your role is to:\n"
                    "1. Break down the project into phases and milestones\n"
                    "2. Create a realistic timeline with deadlines\n"
                    "3. Consider team size and complexity\n"
                    "4. Identify critical path and dependencies\n"
                    "Format the timeline in a clear, structured way."
                ),
                message_window_size=10,
                model=mistral_model,
            )
            timeline_resp = planner.step(
                f"Create a detailed project timeline for this project:\n\n{project_context}"
            )
            st.session_state.timeline = timeline_resp.msgs[0].content

        # Save all details into session_state
        st.session_state.project_name = project_name
        st.session_state.project_type = project_type
        st.session_state.team_size = team_size
        st.session_state.start_date = start_date
        st.session_state.technologies = tech_stack
        st.session_state.description = project_description
        st.session_state.generated = True

# ─── STEP 6: Display results & allow editing ───
if st.session_state.generated:
    st.markdown("### 🏗️ Technical Architecture")
    st.markdown(st.session_state.architecture)

    st.markdown("### 📅 Project Timeline (Raw Text)")
    st.markdown(st.session_state.timeline)

    st.markdown("---")
    st.subheader("✏️ Edit Project Plan")
    edit_tab1, edit_tab2 = st.tabs(["Edit Architecture", "Edit Timeline"])

    with edit_tab1:
        edited_architecture = st.text_area(
            "Edit Technical Architecture",
            value=st.session_state.architecture,
            height=300
        )
        if st.button("Save Architecture Changes", key="save_arch"):
            st.session_state.architecture = edited_architecture
            st.success("Architecture changes saved!")

    with edit_tab2:
        edited_timeline = st.text_area(
            "Edit Project Timeline (Raw Markdown/Text)",
            value=st.session_state.timeline,
            height=300
        )
        if st.button("Save Timeline Changes", key="save_timeline"):
            st.session_state.timeline = edited_timeline
            st.success("Timeline changes saved!")

    # ─ Download the PDF ─
    st.markdown("---")
    st.subheader("📄 Download Project Plan")
    pdf_bytes = generate_pdf()
    if pdf_bytes:
        st.download_button(
            label="📥 Download PDF",
            data=pdf_bytes,
            file_name=f"project_plan_{st.session_state.project_name.replace(' ', '_')}.pdf",
            mime="application/pdf",
            key="download_pdf"
        )

st.markdown("---")
st.markdown("Made with ❤️ using CAMEL-AI 🐫")