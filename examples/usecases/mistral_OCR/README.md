# CAMEL-AI OCR Demo (w/ Mistral)

A simple Streamlit app to extract and summarize text from PDFs and images using the [Mistral OCR](https://mistral.ai/research/mistral-ocr/) API, fully powered by the [CAMEL-AI](https://github.com/camel-ai/camel) framework.

---

## 🚀 Features

- Drag & drop PDF or image upload (up to 200MB)
- Live preview (PDF or image) in the sidebar
- One-click OCR extraction via Mistral OCR
- Nicely formatted OCR result in markdown
- Optional LLM-powered summary using CAMEL-AI’s agents
- Easy Mistral API key input (sidebar)
- Modern Streamlit UI, ready to customize

---

## 🛠️ Requirements

- Python **3.10** or **3.12** (recommended)
- [CAMEL-AI](https://github.com/camel-ai/camel) (`camel-ai==0.2.61`, installed via `requirements.txt`)
- [mistralai](https://pypi.org/project/mistralai/) (for API calls)
- [Streamlit](https://streamlit.io/)
- [Pillow](https://pypi.org/project/Pillow/) (image preview)

Install all dependencies in a **clean virtualenv**.

---

### 📦 Quick Install

```bash
# 1. (Recommended) Create and activate virtualenv
python3.12 -m venv .venv
source .venv/bin/activate

# 2. Clone this demo repo or copy app.py and requirements.txt
# (Assume you’re in the right directory)

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

---

### 📝 Usage

1. **Get your [Mistral API Key](https://console.mistral.ai/home)**
2. **Run the Streamlit app:**
    ```bash
    streamlit run app.py
    ```
3. **Open the app in your browser at** [http://localhost:8501](http://localhost:8501)
4. **Paste your API key** in the sidebar, upload a PDF/image, and extract text!

---

### 📁 File Structure

```
app.py            # Main Streamlit app
README.md         # This file
requirements.txt  # Python dependencies
```

---

## 🔧 Troubleshooting

- **MistralReader import error?**  
  Make sure you have `camel-ai==0.2.61` installed (see `requirements.txt`).
- **No module named mistralai?**  
  Install with `pip install mistralai`.
- **Python version errors?**  
  Use Python 3.10 or 3.12 only.

---

## requirements.txt

```
streamlit
pillow
mistralai
camel-ai[all]==0.2.61
```
