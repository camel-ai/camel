# 🎥 YouTube Video Q&A with CAMEL (Audio + Visual OCR)

This project allows users to enter a YouTube URL and ask questions about the video's **spoken content** and **on-screen text (e.g. PPT slides)**. It combines:

- ✅ Audio transcription via Whisper
- 🖼️ Visual OCR from extracted video frames
- 🧠 CAMEL AI multi-agent reasoning
- 🌐 Streamlit interface for interaction

---

## 🚀 Features

- Downloads YouTube videos via CAMEL toolkit
- Transcribes audio using OpenAI Whisper
- Extracts key video frames every few seconds
- Runs OCR on frames to extract visible text
- Merges transcript + OCR as knowledge
- Lets user ask questions answered by CAMEL agent

---

## 📦 Requirements

Install Python packages:

```bash
pip install -U camel-ai[all] openai-whisper pytesseract streamlit opencv-python python-dotenv
```

### 🧰 Also install system dependencies:

**Tesseract OCR:**

- Windows: [Download here](https://github.com/UB-Mannheim/tesseract/wiki)
- macOS:
  ```bash
  brew install tesseract
  ```
- Ubuntu:
  ```bash
  sudo apt-get install tesseract-ocr
  ```

**FFmpeg** (required by Whisper and frame extraction):

- Windows: [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html) (add `/bin` to PATH)
- macOS:
  ```bash
  brew install ffmpeg
  ```
- Ubuntu:
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

Make sure the path is correct.

---

## 🧪 Run the App

```bash
streamlit run app.py
```

Then open the Streamlit interface in your browser.

---

## 📁 File Structure

```
app.py          # Main Streamlit app
README.md            # This file
```

---

## 🧠 Powered By

- [CAMEL-AI](https://github.com/camel-ai/camel)
- [Whisper by OpenAI](https://github.com/openai/whisper)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
- Streamlit

---

## 💬 Example Usage

1. Paste a YouTube link of a tech tutorial with slides.
2. Ask: _"What is the title of the slide shown at 5 minutes?"_
3. App returns relevant text from OCR and transcript.

---
