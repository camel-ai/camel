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


# Load camel and mistral logo images as base64
def get_base64_img(path, w=32):
    with open(path, "rb") as img_f:
        b64 = base64.b64encode(img_f.read()).decode()
    return f"<img src='data:image/png;base64,{b64}' width='{w}' style='vertical-align:middle;margin-bottom:4px;'>"

camel_logo = get_base64_img("assets/CAMEL_logo.jpg", 40)
mistral_logo = get_base64_img("assets/mistral_logo.png", 40)


# --- Page config ---
st.markdown(
    f"""
    <div style='display:flex; align-items:center; gap:12px;'>
        <span style="font-size:2.7rem;font-weight:700;">Chat with Your OCR Docs with</span>
        {camel_logo}
        {mistral_logo}
    </div>
    """,
    unsafe_allow_html=True
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
        st.session_state.pop("chat_history", None)
        st.experimental_rerun()

    if st.sidebar.button("Extract Text 🔍"):
        with st.spinner("Running OCR…"):
            try:
                loader = MistralReader()
                ocr_response = loader.extract_text(file_path)
                st.session_state['ocr_result'] = ocr_response
                st.session_state['file_path'] = file_path
                st.session_state['chat_history'] = []  # Reset chat on new doc
            except Exception as e:
                st.error(f"❌ OCR failed: {e}")

# --- Show OCR Results (expand/collapse if needed) ---
if 'ocr_result' in st.session_state:
    with st.expander("🔎 OCR Result (Full Extracted Markdown)", expanded=False):
        resp = st.session_state['ocr_result']
        for page in resp.pages:
            if page.markdown:
                st.markdown(page.markdown)
            if page.images:
                st.markdown("**Extracted Images:**")
                for img_obj in page.images:
                    img_path = img_obj.id
                    if os.path.exists(img_path):
                        st.image(img_path)
        st.write("**Model:**", resp.model)
        usage = getattr(resp, 'usage_info', None)
        if usage:
            st.write(f"**Pages Processed:** {usage.pages_processed}")
            st.write(f"**Document Size (bytes):** {usage.doc_size_bytes}")

# --- Chatbot Section ---
if 'ocr_result' in st.session_state:
    # Combine markdown of all pages for context
    resp = st.session_state['ocr_result']
    ocr_context = "\n\n".join([page.markdown or '' for page in resp.pages])

    # Setup LLM agent
    mistral_model = ModelFactory.create(
        model_platform=ModelPlatformType.MISTRAL,
        model_type=ModelType.MISTRAL_LARGE,
        model_config_dict=MistralConfig(temperature=0.0).as_dict(),
    )
    agent = ChatAgent(
        system_message="You are a helpful document assistant. Always answer based only on the provided OCR document.",
        message_window_size=10,
        model=mistral_model,
    )

    # Persistent chat history
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    st.markdown("---")
    st.header("💬 Chat with Document")

    for chat in st.session_state["chat_history"]:
        with st.chat_message(chat["role"]):
            st.markdown(chat["content"])

    user_prompt = st.chat_input("Ask anything about your document...")
    if user_prompt:
        # Show user message
        st.session_state["chat_history"].append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        # Compose prompt with OCR context
        prompt = (
            "Given the following document content (extracted by OCR):\n\n"
            + ocr_context[:3500]  # Keep context in-token limit
            + f"\n\nQuestion: {user_prompt}"
        )

        # Get assistant response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = agent.step(prompt)
                answer = response.msgs[0].content
                st.markdown(answer)
                st.session_state["chat_history"].append({"role": "assistant", "content": answer})

# --- Footer ---
st.markdown("---")
st.markdown("Made with ❤️ using CAMEL-AI & Mistral OCR 🐫")

