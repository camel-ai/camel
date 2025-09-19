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

import streamlit as st
import ffmpeg
from camel.toolkits.video_download_toolkit import VideoDownloaderToolkit
from camel.toolkits.audio_analysis_toolkit import AudioAnalysisToolkit
from camel.agents import ChatAgent
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize toolkits
video_downloader = VideoDownloaderToolkit(working_directory="downloads/")
audio_toolkit = AudioAnalysisToolkit(cache_dir="downloads/")
summarizer_agent = ChatAgent(system_message="You are a helpful assistant that summarizes transcripts.", model="gpt-4o-mini")
qa_agent = ChatAgent(system_message="Answer the question based on the context provided.", model="gpt-4o-mini")

st.title("🎥 Video Content Q&A with CAMEL")

# Input URL
url = st.text_input("Enter a YouTube video URL:",value="https://www.youtube.com/watch?v=hT_nvWreIhg")

if st.button("Process Video"):
    if url:
        with st.spinner("Downloading and processing video..."):
            # Download video
            video_path = video_downloader.download_video(url)
            st.video(video_path)

            # Extract audio
            audio_path = os.path.splitext(video_path)[0] + ".wav"
            ffmpeg.input(video_path).output(audio_path, ac=1, ar=16000).run(overwrite_output=True)
            
            # Transcribe
            transcript = audio_toolkit.audio2text(audio_path)

            # Summarize
            summary = summarizer_agent.step(transcript)
            st.subheader("📝 Summary")
            st.write(summary)

            # Store transcript for Q&A
            st.session_state.transcript = transcript
            st.session_state.qa_agent = qa_agent

if "transcript" in st.session_state:
    st.subheader("💬 Ask Questions about the Video")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    user_q = st.text_input("Your question:")

    if user_q:
        transcript = st.session_state.transcript
        prompt = f"Context: {transcript}\n\nQuestion: {user_q}"
        answer = st.session_state.qa_agent.step(prompt).msgs[0].content

        st.session_state.chat_history.append((user_q, answer))

    for q, a in st.session_state.chat_history:
        st.markdown(f"**User:** {q}")
        st.markdown(f"**AI:** {a}")
