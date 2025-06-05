import os
import streamlit as st
import json
import base64

from camel.toolkits.pptx_toolkit import PPTXToolkit
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.agents import ChatAgent

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
    return f"""
You are an expert PowerPoint slide generator for CAMEL PPTXToolkit. 

Your job: Output a single JSON array (no markdown, no commentary) for a presentation on "{topic}" with exactly {slide_count + 1} slides (including title). 

CAMEL PPTXToolkit slide types (choose from these only):
- Title slide:
  {{"title": ..., "subtitle": ...}}
- Bullet slide:
  {{"heading": ..., "bullet_points": ["...", "..."], "img_keywords": "..."}}
- Step-by-step slide:
  {{"heading": ..., "bullet_points": [">> Step 1: ...", ">> Step 2: ...", ">> Step 3: ..."], "img_keywords": "..."}}
  (If a bullet starts with ">>", it's rendered as a pentagon/chevron shape.)
- Table slide:
  {{"heading": ..., "table": {{"headers": [...], "rows": [[...],[...],[...]]}}, "img_keywords": "..."}}

REQUIRED FORMAT:
[
  {{"title": "Title for {topic}", "subtitle": "Subtitle for this topic"}},
  {{"heading": "...", "bullet_points": ["...", "..."], "img_keywords": "..."}},
  {{"heading": "...", "bullet_points": [">> Step 1: ...", ">> Step 2: ..."], "img_keywords": "..."}},
  {{"heading": "...", "table": {{"headers": ["Col1", "Col2"], "rows": [["A", "B"], ["C", "D"]]}}, "img_keywords": "..."}},
  ...
]

MANDATORY RULES:
1. The first slide is always a title slide.
2. Include at least one step-by-step slide (with all bullet points starting with ">>").
3. Include at least one table slide.
4. At least TWO slides (not counting the title slide) MUST have non-empty, relevant "img_keywords" (search terms, not URLs) for the image field. Use visually interesting or topic-relevant keywords.
5. For all bullet slides, use Markdown syntax for bold (**text**) and italics (*text*).
6. Make content clear, concise, and visually engaging.
7. Do NOT output markdown code fences or commentary—only raw JSON array.

Styling Note: Slides will be rendered with a dark background and white text (no need to mention this, just make sure content is readable).
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
            model_type=ModelType.GPT_4O,
            model_config_dict={"temperature": 0.0},
        )
    )
   

    # 3. Call the agent with our instruction prompt
    try:
        response = agent.step(full_prompt)
        content = response.msgs[0].content.strip()

        # 4. Strip any accidental code fences, then parse JSON
        json_str = content
        if json_str.startswith("```"):
            json_str = json_str.split("```")[1].strip()
        if not json_str.startswith("["):
            json_str = json_str[json_str.index("[") :]
        if json_str.rfind("]") != -1:
            json_str = json_str[: json_str.rfind("]") + 1]

        slides = json.loads(json_str)
        if not isinstance(slides, list) or not slides or "title" not in slides[0]:
            raise ValueError("Invalid JSON structure")
        return slides, None

    except Exception as e:
        return None, f"❌ ChatAgent (OpenAI) call failed: {e}"

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
    st.info("🕒 Generating slide JSON with ChatAgent (GPT-4o)...")
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
