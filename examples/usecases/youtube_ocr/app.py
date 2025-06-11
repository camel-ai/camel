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

import ffmpeg, cv2, whisper, pytesseract, streamlit as st
from camel.toolkits.video_download_toolkit import VideoDownloaderToolkit
from camel.agents import ChatAgent
from camel.messages import BaseMessage
from PIL import Image
from dotenv import load_dotenv
import os

load_dotenv()
pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_CMD", "tesseract")


# Initialize CAMEL tools/agent
video_tool = VideoDownloaderToolkit()
agent = ChatAgent()

def process_video(url, question):
    video_path = video_tool.download_video(url)
    # Extract audio
    audio_path = "audio.wav"
    ffmpeg.input(video_path).output(audio_path, acodec='pcm_s16le', ac=1, ar='16k').run()
    # Transcribe
    model = whisper.load_model("base")
    transcript = model.transcribe(audio_path)["text"]
    # Extract frames every 4s
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS); interval = 4
    frames = []
    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret: break
        if frame_count % int(fps*interval) == 0:
            fname = f"frame_{frame_count}.png"
            cv2.imwrite(fname, frame)
            frames.append(fname)
        frame_count += 1
    cap.release()
    # OCR on frames
    ocr_texts = []
    for img_path in frames:
        text = pytesseract.image_to_string(Image.open(img_path))
        ocr_texts.append(text)
    ocr_content = "\n".join(ocr_texts)
    # Prepare context and query agent
    knowledge = f"Transcript:\n{transcript}\n\nOn-screen Text:\n{ocr_content}"
    user_msg = BaseMessage.make_user_message(role_name="User", 
                content=f"{knowledge}\n\nQuestion: {question}")
    response = agent.step(user_msg)
    return response.msgs[0].content

# Streamlit UI
st.title("YouTube Video Q&A with CAMEL")
youtube_url = st.text_input("YouTube URL:")
user_q = st.text_input("Your Question:")
if st.button("Ask"):
    answer = process_video(youtube_url, user_q)
    st.write(answer)
