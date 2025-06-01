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
from PIL import Image
import tempfile
import base64

from camel.loaders import MistralReader
from camel.configs import MistralConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.agents import ChatAgent

# --- Page config ---
st.set_page_config(
    page_title="Create Document Summarization Agents with Mistral OCR & CAMEL-AI 🐫",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Sidebar: API Key & Upload & Preview ---
st.sidebar.header("⚙️ Configuration")
api_key = st.sidebar.text_input(
    "Mistral API Key", type="password", help="Get it from https://console.mistral.ai/home"
)
if api_key:
    os.environ["MISTRAL_API_KEY"] = api_key

st.sidebar.markdown("---")
st.sidebar.header("📤 Upload Document")
uploaded = st.sidebar.file_uploader(
    "Choose a PDF or Image…", type=["pdf", "png", "jpg", "jpeg"]
)

# Display PDF or Image preview in sidebar
file_path = None
if uploaded:
    ext = uploaded.name.split('.')[-1].lower()
    if ext in ["png", "jpg", "jpeg"]:
        image = Image.open(uploaded)
        st.sidebar.image(image, caption="Uploaded Image Preview", use_container_width=True)
        tmp_pdf = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        image.convert("RGB").save(tmp_pdf.name)
        file_path = tmp_pdf.name
    else:
        tmp_pdf = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        with open(tmp_pdf.name, "wb") as f:
            f.write(uploaded.getbuffer())
        file_path = tmp_pdf.name
        with open(file_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')
        pdf_html = (
            f'<iframe src="data:application/pdf;base64,{b64}" '
            'width="100%" height="300px" type="application/pdf"></iframe>'
        )
        st.sidebar.markdown("### PDF Preview")
        st.sidebar.markdown(pdf_html, unsafe_allow_html=True)

    if st.sidebar.button("Clear Result"):
        st.session_state.pop("ocr_result", None)
        st.session_state.pop("file_path", None)
        st.experimental_rerun()

    if st.sidebar.button("Extract Text 🔍"):
        with st.spinner("Running OCR…"):
            try:
                loader = MistralReader()
                ocr_response = loader.extract_text(file_path)
                st.session_state['ocr_result'] = ocr_response
                st.session_state['file_path'] = file_path
            except Exception as e:
                st.error(f"❌ OCR failed: {e}")

# --- Main UI ---
st.title("Create Document Summarization Agents with Mistral OCR & CAMEL-AI 🐫")
st.markdown("Upload a PDF or image via the sidebar, preview it there, and extract text, then summarize it with a CAMEL agent.")

# --- Show OCR Results ---
st.markdown("---")
if 'ocr_result' in st.session_state:
    resp = st.session_state['ocr_result']
    st.subheader("🔎 OCR Result")
    try:
        for page in resp.pages:
            if page.markdown:
                st.markdown(page.markdown)
            if page.images:
                st.markdown("**Extracted Images:**")
                for img_obj in page.images:
                    img_path = img_obj.id
                    if os.path.exists(img_path):
                        st.image(img_path)
    except Exception:
        st.json(resp)

    st.write("**Model:**", resp.model)
    usage = getattr(resp, 'usage_info', None)
    if usage:
        st.write(f"**Pages Processed:** {usage.pages_processed}")
        st.write(f"**Document Size (bytes):** {usage.doc_size_bytes}")

# --- Optional: Quick Summary ---
st.markdown("---")
if 'ocr_result' in st.session_state:
    st.subheader("🤖 Quick Summary")
    mistral_model = ModelFactory.create(
        model_platform=ModelPlatformType.MISTRAL,
        model_type=ModelType.MISTRAL_LARGE,
        model_config_dict=MistralConfig(temperature=0.0).as_dict(),
    )
    agent = ChatAgent(
        system_message="You are a helpful document assistant.",
        message_window_size=10,
        model=mistral_model,
    )
    if st.button("Summarize Document"):
        with st.spinner("Generating summary…"):
            text = []
            for page in resp.pages:
                text.append(page.markdown or '')
            prompt_text = "\n---\n".join(text)[:4000]
            summary = agent.step(f"Summarize this document concisely:\n\n{prompt_text}")
            st.markdown(summary.msgs[0].content)

# --- Footer ---
st.markdown("---")
st.markdown("Made with ❤️ using CAMEL-AI & Mistral OCR 🐫")
