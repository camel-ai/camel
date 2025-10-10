# 🖥️ System Performance Monitor with CAMEL Agents & Streamlit

This application provides a user-friendly interface to monitor system performance metrics, emphasizing disk usage. It leverages:

- 🧠 **CAMEL AI Agents** for executing terminal commands and analyzing outputs
- 🛠️ **TerminalToolkit** to interface with the system's terminal
- 🌐 **Streamlit** for an interactive web-based UI

---

## 🚀 Features

- **Disk Usage Retrieval**: Executes terminal commands to fetch disk usage statistics.
- **AI-Powered Analysis**: Utilizes CAMEL AI agents to interpret and summarize terminal outputs.
- **Interactive Interface**: Streamlit-based UI for seamless user interaction.

---

## 📦 Requirements

Ensure you have the necessary Python packages installed:

```bash
pip install -r requirements.txt
```

---

## 🛠️ Setup

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/camel-ai/camel.git
   cd examples/usecases/terminal_toolkit_usecase
   ```

2. **Install Dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:

   Create a `.env` file in the root directory and add your OpenAI API key:

   ```env
   OPENAI_API_KEY=your_openai_api_key
   ```

---

## 🧪 Run the App

Start the Streamlit application:

```bash
streamlit run app.py
```

Then, navigate to the provided URL in your browser to interact with the app.

---

## 📁 File Structure

```
├── app.py             # Main Streamlit application
├── requirements.txt   # Python dependencies
├── .env               # Environment variables
└── README.md          # Project documentation
```

---

## 🧠 Powered By

- [CAMEL AI](https://github.com/camel-ai/camel): Multi-agent reasoning framework.
- [Streamlit](https://streamlit.io/): Web application framework for Python.

---

## 💬 Example Usage

1. **Initiate Analysis**: Click the "Run System Analysis" button.
2. **Process**:
   - The app executes terminal commands to retrieve disk usage metrics.
   - CAMEL AI agents analyze the raw terminal output.
3. **Output**: Displays both the raw terminal output and a summarized analysis of system health.

---

## 📌 Notes

- Ensure your OpenAI API key is valid and has sufficient quota.
- The accuracy of the analysis depends on the system's current state and the capabilities of the CAMEL AI agents.
- Always review the analysis results, especially before making critical system decisions.

---

## 🙌 Acknowledgements

- [CAMEL AI](https://github.com/camel-ai/camel) for the multi-agent reasoning framework.
- [Streamlit](https://streamlit.io/) for the intuitive web interface.

---

Feel free to contribute to this project by submitting issues or pull requests.
