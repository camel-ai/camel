import os
import streamlit as st
import tempfile
import json
from camel.toolkits.pptx_toolkit import PPTXToolkit
import openai

# --- Streamlit Page Config ---
st.set_page_config(
    page_title="AI-Powered PPTX Generator (CAMEL-AI)",
    page_icon="📑",
    layout="centered"
)

st.title("Create Beautiful PPTs from Any Topic 🌟")
st.markdown(
    "Enter a topic, provide your API keys, and get a professional PPTX auto-generated using AI + the PPTX Toolkit."
)

# --- Sidebar Config ---
st.sidebar.header("⚙️ Configuration")
openai_key = st.sidebar.text_input(
    "OpenAI API Key", type="password", help="Get yours at https://platform.openai.com/account/api-keys"
)
pexels_key = st.sidebar.text_input(
    "Pexels API Key", type="password", help="(Optional) Needed if you want images fetched from Pexels"
)

# --- User Input ---
st.header("1. Enter Your Presentation Topic")
topic = st.text_input("Topic (e.g., ‘Blockchain for Beginners’)")
slide_count = st.slider("Number of slides (excluding title slide)", 3, 10, 5)

# --- Construct OpenAI Prompt ---
def pptx_prompt(topic: str, slide_count: int) -> str:
    return f"""
You are an expert PowerPoint slide generator for CAMEL PPTXToolkit. 

**Your job:** Output a single JSON array (no markdown, no commentary) for a presentation on "{topic}" with exactly {slide_count+1} slides (including title). 

**CAMEL PPTXToolkit slide types (choose from these only):**
- **Title slide:** 
  {{"title": ..., "subtitle": ...}}
- **Bullet slide:** 
  {{"heading": ..., "bullet_points": ["...", "..."], "img_keywords": "..."}}
- **Step-by-step slide:** 
  {{"heading": ..., "bullet_points": [">> Step 1: ...", ">> Step 2: ...", ">> Step 3: ..."], "img_keywords": "..."}}
  (If a bullet starts with ">>", it's rendered as a pentagon/chevron shape.)
- **Table slide:** 
  {{"heading": ..., "table": {{"headers": [...], "rows": [[...],[...],[...]]}}, "img_keywords": "..."}}

**REQUIRED FORMAT:**
[
  {{"title": "Title for {topic}", "subtitle": "Subtitle for this topic"}},
  {{"heading": "...", "bullet_points": ["...", "..."], "img_keywords": "..."}},
  {{"heading": "...", "bullet_points": [">> Step 1: ...", ">> Step 2: ..."], "img_keywords": "..."}},
  {{"heading": "...", "table": {{"headers": ["Col1", "Col2"], "rows": [["A", "B"], ["C", "D"]]}}, "img_keywords": "..."}},
  ...
]

**MANDATORY RULES:**
1. The first slide is always a title slide.
2. Include at least one step-by-step slide (with all bullet points starting with ">>").
3. Include at least one table slide.
4. At least TWO slides (not counting the title slide) MUST have non-empty, relevant "img_keywords" (search terms, not URLs) for the image field. Use visually interesting or topic-relevant keywords.
5. For all bullet slides, use Markdown syntax for bold (**text**) and italics (*text*).
6. Make content clear, concise, and visually engaging. 
7. Do NOT output markdown code fences or commentary—only raw JSON array.

**Styling Note:** Slides will be rendered with a dark background and white text (no need to mention this, just make sure content is readable).

**Example:**
[
  {{"title": "AI Agents", "subtitle": "Exploring the world of artificial intelligence agents"}},
  {{"heading": "Types of AI Agents", "bullet_points": ["Intelligent Virtual Agents", "Autonomous Agents", "Collaborative Agents"], "img_keywords": "AI, technology"}},
  {{"heading": "Creating an AI Agent", "bullet_points": [">> Step 1: Define the goal", ">> Step 2: Choose algorithms", ">> Step 3: Implement and test"], "img_keywords": "workflow, robotics"}},
  {{"heading": "Comparison of AI Agents", "table": {{"headers": ["Type", "Capabilities", "Examples"], "rows": [["Virtual", "Conversational AI", "Siri"], ["Autonomous", "Self-learning", "Robots"]]}}, "img_keywords": "comparison chart, table"}},
  ... (add more if needed) ...
]
"""



# --- Call OpenAI to Generate Slide JSON ---
def generate_pptx_json(topic: str, slide_count: int):
    prompt = pptx_prompt(topic, slide_count)
    try:
        resp = openai.chat.completions.create(
            model="gpt-4.1",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1800,
        )
        content = resp.choices[0].message.content.strip()

        # Strip code fences if any, then parse JSON
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
        return None, f"❌ OpenAI API call failed: {e}"

# --- Build & Return PPTX Bytes ---
def build_pptx(slides):
    # Inject PEXELS_API_KEY from sidebar (can be empty string)
    os.environ["PEXELS_API_KEY"] = pexels_key or ""
    pptx_toolkit = PPTXToolkit(output_dir="outputs")

    # Use a hash to generate a unique filename
    out_name = f"demo_pptx_{abs(hash(json.dumps(slides)))}.pptx"
    result = pptx_toolkit.create_presentation(
        json.dumps(slides),
        out_name
    )
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

openai.api_key = openai_key

if topic and st.button("Generate Presentation"):
    st.info("🕒 Asking OpenAI to generate your slides...")
    slides, error = generate_pptx_json(topic, slide_count)
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
