# 🎥 YouTube Video Q&A with CAMEL (Audio + Visual OCR)

This project enables users to input a YouTube URL and ask questions about the video's **spoken content** and **on-screen text (e.g., PPT slides)**. It integrates:

- ✅ Audio transcription via Whisper
- 🖼️ Visual OCR from extracted video frames
- 🧠 CAMEL AI multi-agent reasoning
- 🌐 Streamlit interface for interaction

---

## 🚀 Features

- Downloads YouTube videos via CAMEL toolkit
- Transcribes audio using OpenAI Whisper
- Extracts key video frames at regular intervals
- Performs OCR on frames to extract visible text
- Combines transcript and OCR data as knowledge
- Allows users to ask questions answered by CAMEL agent

---

## 📦 Requirements

Install Python packages with specific versions:

```bash
pip install -r requirements.txt
```

### 🧰 Also install system dependencies:

**Tesseract OCR:**

- **Windows:** [Download here](https://github.com/UB-Mannheim/tesseract/wiki)
- **macOS:**
  ```bash
  brew install tesseract
  ```
- **Ubuntu:**
  ```bash
  sudo apt-get install tesseract-ocr
  ```

**FFmpeg** (required by Whisper and for frame extraction):

- **Windows:** [Download here](https://ffmpeg.org/download.html) (add `/bin` to PATH)
- **macOS:**
  ```bash
  brew install ffmpeg
  ```
- **Ubuntu:**
  ```bash
  sudo apt-get install ffmpeg
  ```

---

## 🛠️ Setup for Windows

If Tesseract is not found, add this in your Python code:

```python
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

Ensure the path is correct based on your installation.

---

## 🧪 Run the App

```bash
streamlit run app.py
```

Then, open the Streamlit interface in your browser.

---

## 📁 File Structure

```
app.py          # Main Streamlit app
README.md       # This file
requirements.txt  # Python dependencies
```

---

## 🧠 Powered By

- [CAMEL-AI](https://github.com/camel-ai/camel)
- [Whisper by OpenAI](https://github.com/openai/whisper)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
- [Streamlit](https://streamlit.io/)

---

## 💬 Example Usage

1. Paste a YouTube link of a tech tutorial with slides.
2. Ask: _"What is the title of the slide shown at 5 minutes?"_
3. The app returns relevant text from OCR and transcript.

---
