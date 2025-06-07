# 🧠 Codeforces Problem Solver with CAMEL Agents & Firecrawl

This project enables users to input a Codeforces Problem ID and receive an AI-generated Python solution. It integrates:

- 🔍 Web scraping via Firecrawl
- 🤖 Multi-agent reasoning with CAMEL AI
- 🧪 Code execution and validation against sample tests
- 🌐 Streamlit interface for user interaction

---

## 🚀 Features

- **Problem Retrieval**: Fetches problem statements from Codeforces using Firecrawl.
- **Sample Extraction**: Parses and extracts sample inputs and outputs from the problem description.
- **AI-Powered Solution**: Utilizes CAMEL AI agents to generate Python solutions.
- **Automated Testing**: Executes the generated code against extracted samples to verify correctness.

---

## 📦 Requirements

Install Python packages:

```bash
pip install -r requirements.txt
```

---

## 🛠️ Setup

1. **Clone the repository**:

   ```bash
   git clone https://github.com/camel-ai/camel.git
   cd examples/usecases/codeforces_question_solver
   ```

2. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:

   Create a `.env` file in the root directory and add your Firecrawl API key and OpenAI API key:

   ```env
   FIRECRAWL_API_KEY=your_firecrawl_api_key
   OPENAI_API_KEY=your_openai_api_key
   ```

---

## 🧪 Run the App

Start the Streamlit application:

```bash
streamlit run app.py
```

Then, open the provided URL in your browser to interact with the app.

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
- [Firecrawl](https://github.com/mendableai/firecrawl): Web scraping and data extraction tool.
- [Streamlit](https://streamlit.io/): Web application framework for Python.

---

## 💬 Example Usage

1. **Input**: Enter a Codeforces Problem ID (e.g., `2116B`).
2. **Process**:
   - The app fetches the problem statement using Firecrawl.
   - Extracts sample inputs and outputs.
   - Generates a Python solution using CAMEL AI agents.
   - Executes the solution against the samples.
3. **Output**: Displays the problem statement, generated code, and test results indicating pass/fail status.

---

## 📌 Notes

- Ensure your Firecrawl API key is valid and has sufficient quota.
- The accuracy of the generated solutions depends on the complexity of the problem and the capabilities of the CAMEL AI agents.
- Always review and test the generated code before using it in competitive environments.



---

## 🙌 Acknowledgements

- [CAMEL AI](https://github.com/camel-ai/camel) for the multi-agent reasoning framework.
- [Firecrawl](https://github.com/mendableai/firecrawl) for the web scraping capabilities.
- [Streamlit](https://streamlit.io/) for the intuitive web interface.

---

Feel free to contribute to this project by submitting issues or pull requests.
