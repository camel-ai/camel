# 📑 AI-Powered PPTX Generator (CAMEL-AI)

Generate beautiful, professional PowerPoint presentations (PPTX) on any topic in seconds!  
Built with [CAMEL-AI](https://github.com/camel-ai/camel), OpenAI, and Streamlit.

---

## 🚀 Features

- 🔥 Generate engaging, multi-slide PPTX files for any topic—instantly!
- 💡 Uses OpenAI to create bullet, step-by-step (pentagon/chevron), and table slides.
- 🖼️ Optional support for auto-inserting images using [Pexels](https://www.pexels.com/api/).
- 📦 All output is 100% local and ready for download.

---

## 🛠️ Installation

```bash
# 1. Create a fresh virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 2. Install the specific CAMEL-AI version (and requirements)
pip install camel-ai[all]==0.2.62 streamlit openai

# 3. (Optional) Get a [Pexels API key](https://www.pexels.com/api/) if you want slides with images
```

---

## 📝 Usage

1. **Get your OpenAI API key:**  
   [Create one here](https://platform.openai.com/account/api-keys).

2. **(Optional) Get your Pexels API key:**  
   [Request it here](https://www.pexels.com/api/) if you want to auto-insert images.

3. **Clone this repo or copy the app file:**
   ```bash
   git clone https://github.com/camel-ai/camel
   cd examples/usecases/pptx_toolkit_usecase
   # Or just copy the .py script to your working directory
   ```

4. **Run the Streamlit app:**
   ```bash
   streamlit run app_pptx.py
   ```

5. **Open the Streamlit UI in your browser** (default: http://localhost:8501).

6. **Enter your API keys, type your topic, set slide count, and hit "Generate Presentation"!**

---

## 🏗️ How it Works

- You provide a topic and desired slide count.
- The app prompts OpenAI GPT-4o or GPT-4 (you can change the model in code) to generate slide content in a format CAMEL-AI's `PPTXToolkit` can use.
- At least one step-by-step slide and one table slide are always included; at least two slides will contain images if you provide a Pexels API key.
- The toolkit generates a `.pptx` file named after your topic, ready for download.

---

## ⚙️ Example Prompt Structure

<details>
<summary>See Example</summary>

```json
[
  {"title": "AI Agents", "subtitle": "Exploring the world of artificial intelligence agents"},
  {"heading": "Types of AI Agents", "bullet_points": ["Intelligent Virtual Agents", "Autonomous Agents", "Collaborative Agents"], "img_keywords": "AI, technology"},
  {"heading": "Creating an AI Agent", "bullet_points": [">> Step 1: Define the goal", ">> Step 2: Choose algorithms", ">> Step 3: Implement and test"], "img_keywords": "workflow, robotics"},
  {"heading": "Comparison of AI Agents", "table": {"headers": ["Type", "Capabilities", "Examples"], "rows": [["Virtual", "Conversational AI", "Siri"], ["Autonomous", "Self-learning", "Robots"]]}, "img_keywords": "comparison chart, table"}
]
```
</details>

---

## 📝 Credits

- Built with [CAMEL-AI](https://github.com/camel-ai/camel) (PPTXToolkit module)
- Powered by [OpenAI](https://platform.openai.com/docs/api-reference) (for content generation)
- Images by [Pexels](https://www.pexels.com/api/) (optional)
- UI by [Streamlit](https://streamlit.io/)

---

## 🐪 License

Apache 2.0  
(c) 2023-2024 [CAMEL-AI.org](https://camel-ai.org)

---

*Made with ❤️ by the CAMEL-AI community.*
