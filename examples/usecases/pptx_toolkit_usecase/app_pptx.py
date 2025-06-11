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
import os
import streamlit as st
import json
import base64
from typing import List, Optional, Union
from pydantic import BaseModel, Field


from camel.toolkits.pptx_toolkit import PPTXToolkit
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.agents import ChatAgent

# --- Pydantic Models for Structured Output ---
class TitleSlide(BaseModel):
    """Title slide model"""
    title: str = Field(description="Main title of the presentation")
    subtitle: str = Field(description="Subtitle or description")

class TableData(BaseModel):
    """Table data model"""
    headers: List[str] = Field(description="Table column headers")
    rows: List[List[str]] = Field(description="Table rows data")

class BulletSlide(BaseModel):
    """Bullet point slide model"""
    heading: str = Field(description="Slide heading")
    bullet_points: List[str] = Field(description="List of bullet points, use >> prefix for step-by-step slides")
    img_keywords: Optional[str] = Field(default="", description="Keywords for image search (not URLs)")

class TableSlide(BaseModel):
    """Table slide model"""
    heading: str = Field(description="Slide heading")
    table: TableData = Field(description="Table data with headers and rows")
    img_keywords: Optional[str] = Field(default="", description="Keywords for image search (not URLs)")

class PresentationSlides(BaseModel):
    """Complete presentation model"""
    title_slide: TitleSlide = Field(description="First slide must be a title slide")
    content_slides: List[Union[BulletSlide, TableSlide]] = Field(
        description="Content slides including bullet slides and table slides"
    )


# Load camel logo as base64
def get_base64_img(path, w=32):
    with open(path, "rb") as img_f:
        b64 = base64.b64encode(img_f.read()).decode()
    return f"<img src='data:image/png;base64,{b64}' width='{w}' style='vertical-align:middle;margin-bottom:4px;'>"

camel_logo = get_base64_img("assets/CAMEL_logo.jpg", 40)

# --- Page config ---
st.markdown(
    f"""
    <div style='display:flex; align-items:center; gap:12px;'>
        <span style="font-size:2.2rem;font-weight:700;">PPTX Generator using pptx_toolkit with</span>
        {camel_logo}
    </div>
    """,
    unsafe_allow_html=True
)

# --- Sidebar Config ---
st.sidebar.header("⚙️ Configuration")
openai_key = st.sidebar.text_input(
    "OpenAI API Key (for ChatAgent/OpenAI backend)", type="password",
    help="Get yours at https://platform.openai.com/account/api-keys"
)
pexels_key = st.sidebar.text_input(
    "Pexels API Key", type="password", help="(Optional) Needed if you want images fetched from Pexels"
)

# --- User Input ---
st.header("1. Enter Your Presentation Topic")
topic = st.text_input("Topic (e.g., ‘Blockchain for Beginners’)")
slide_count = st.slider("Number of slides (excluding title slide)", 3, 10, 5)

# --- Construct the JSON‐generation instructions ---
def pptx_prompt(topic: str, slide_count: int) -> str:
    r"""Create a prompt for structured output generation"""
    return f"""
Create a presentation about "{topic}" with exactly {slide_count + 1} slides total (1 title slide + {slide_count} content slides).
Requirements:
1. First slide must be a title slide with appropriate title and subtitle
2. Include at least one step-by-step slide (bullet points starting with ">>")
3. Include at least one table slide with relevant data
4. At least TWO content slides must have meaningful img_keywords for visual content
5. Use Markdown formatting (**bold**, *italic*) in bullet points
6. Make content clear, concise, and engaging for the topic "{topic}"
The presentation should cover key aspects of {topic}, including practical information, processes, and relevant data.
"""

# --- Generate Slide JSON via ChatAgent ---
def generate_pptx_json_with_agent(topic: str, slide_count: int, api_key: str):
    # 1. Build the full instruction prompt
    full_prompt = pptx_prompt(topic, slide_count)

    # 2. Instantiate a ChatAgent pointing at OpenAI GPT-4o
    os.environ["OPENAI_API_KEY"] = api_key
    agent = ChatAgent(
        system_message="You are an AI Assistant that strictly follows instructions to produce only valid JSON for slides.",
        message_window_size=5,
        model=ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_4_1,
            model_config_dict={"temperature": 0.0},
        )
    )

    # 3. Call the agent with our instruction prompt
    try:
        response = agent.step(full_prompt,response_format=PresentationSlides)

        # Parse JSON string into Pydantic object
        json_content = response.msgs[0].content
        presentation_data = PresentationSlides.model_validate_json(json_content)

        # Convert to the expected JSON format
        slides_json = []

        # Add title slide
        slides_json.append({
            "title": presentation_data.title_slide.title,
            "subtitle": presentation_data.title_slide.subtitle
        })

        # Add content slides
        for slide in presentation_data.content_slides:
            if isinstance(slide, BulletSlide):
                slides_json.append({
                    "heading": slide.heading,
                    "bullet_points": slide.bullet_points,
                    "img_keywords": slide.img_keywords or ""
                })
            elif isinstance(slide, TableSlide):
                slides_json.append({
                    "heading": slide.heading,
                    "table": {
                        "headers": slide.table.headers,
                        "rows": slide.table.rows
                    },
                    "img_keywords": slide.img_keywords or ""
                })

        return slides_json, None

    except Exception as e:
        return None, f"❌ Structured output generation failed: {e}"

# --- Build & Return PPTX Bytes ---
def build_pptx(slides):
    os.environ["PEXELS_API_KEY"] = pexels_key or ""
    pptx_toolkit = PPTXToolkit(output_dir="outputs")

    out_name = f"demo_pptx_{abs(hash(json.dumps(slides)))}.pptx"
    result = pptx_toolkit.create_presentation(json.dumps(slides), out_name)
    pptx_path = os.path.join("outputs", out_name)
    if os.path.exists(pptx_path):
        with open(pptx_path, "rb") as f:
            return f.read(), out_name, result
    else:
        return None, None, result

# --- Main App Logic ---
if not openai_key:
    st.info("Please enter your OpenAI API key in the sidebar to continue.")
    st.stop()

if topic and st.button("Generate Presentation"):
    st.info("🕒 Generating slide JSON with ChatAgent (GPT-4.1)...")
    slides, error = generate_pptx_json_with_agent(topic, slide_count, openai_key)
    if error:
        st.error(error)
        st.stop()

    st.success("✅ Slide JSON created! Now building PPTX...")
    pptx_bytes, fname, pptx_result = build_pptx(slides)

    if pptx_bytes:
        st.success("🎉 Your presentation is ready!")
        st.download_button(
            label=f"Download {fname}",
            data=pptx_bytes,
            file_name=fname,
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
    else:
        st.error(f"PPTX generation failed: {pptx_result}")

st.markdown("---")
st.caption("Made with ❤️ using CAMEL-AI, OpenAI & PPTXToolkit")