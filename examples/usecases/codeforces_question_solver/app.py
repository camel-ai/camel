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
import re
import streamlit as st
from dotenv import load_dotenv
from firecrawl import FirecrawlApp
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import CodeExecutionToolkit, MathToolkit
from camel.types import ModelPlatformType, ModelType
from camel.logger import set_log_level

set_log_level(level="DEBUG")

# Load environment variables
load_dotenv()

st.title("🤖 Codeforces Solver using CAMEL Agents with Firecrawl")

problem_id = st.text_input("Enter Codeforces Problem ID (e.g., 2116B):")

def extract_samples(markdown):
    # Enhanced pattern to match 'Input' and 'Output' sections with code blocks
    pattern = re.compile(
        r'###\s*Input\s*```(?:\w+)?\s*(.*?)```.*?###\s*Output\s*```(?:\w+)?\s*(.*?)```',
        re.DOTALL
    )
    matches = pattern.findall(markdown)
    samples = []
    for inp, out in matches:
        inp_clean = inp.strip()
        out_clean = out.strip()
        if inp_clean and out_clean:
            samples.append((inp_clean, out_clean))
    return samples

if st.button("Solve Problem") and problem_id:
    try:
        contest_id = ''.join(filter(str.isdigit, problem_id))
        index = ''.join(filter(str.isalpha, problem_id)).upper()
        url = f"https://codeforces.com/contest/{contest_id}/problem/{index}"

        FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
        if not FIRECRAWL_API_KEY:
            st.error("Firecrawl API key not found.")
            st.stop()

        # Initialize FirecrawlApp
        app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)
        # Corrected API call with 'params' dictionary
        result = app.scrape_url(url, params={'formats': ['markdown']})
        markdown_content = result.get("markdown", "")
        if not markdown_content:
            st.error("Could not extract problem content.")
            st.stop()

        st.subheader("Problem Statement and Samples")
        st.markdown(markdown_content)

        # Extract samples
        samples = extract_samples(markdown_content)
        if not samples:
            st.warning("⚠️ No sample input/output found.")
        else:
            st.success(f"✅ Found {len(samples)} sample(s).")

        # Create CAMEL Agent with toolkits
        model = ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_4O,
            model_config_dict={"temperature": 0.0}
        )
        code_tools = CodeExecutionToolkit().get_tools()
        math_tools = MathToolkit().get_tools()

        agent = ChatAgent(
            model=model,
            tools=[*code_tools, *math_tools],
            system_message=(
                "You are a competitive programming expert. "
                "Given a Codeforces problem, write correct and optimized Python code. "
                "Use only stdin and stdout for input/output."
            )
        )

        user_query = f"Solve this Codeforces problem. Write Python code that reads from stdin and writes to stdout.\n\n{markdown_content}"
        step = agent.step(user_query)
        response = step.msgs[0].content.strip()

        # Extract code from markdown
        start = response.find("```python")
        end = response.find("```", start + 1)
        code = response[start + len("```python"):end].strip() if start != -1 and end != -1 else response

        st.subheader("Generated Code")
        st.code(code, language='python')

        st.subheader("Sample Test Results")
        exec_toolkit = CodeExecutionToolkit()
        all_passed = True

        for idx, (sample_input, expected_output) in enumerate(samples):
            result = exec_toolkit.run_code(
                code=code,
                input_data=sample_input,
                timeout=5,
            )
            output = result.output.strip()
            expected = expected_output.strip()

            st.markdown(f"**Sample #{idx + 1}**")
            st.text(f"Input:\n{sample_input.strip()}")
            st.text(f"Expected Output:\n{expected}")
            st.text(f"Your Output:\n{output}")
            if output == expected:
                st.success("✅ Passed")
            else:
                st.error("❌ Failed")
                all_passed = False

        if all_passed:
            st.success("🎉 All sample tests passed!")
        else:
            st.warning("⚠️ Some tests failed. Please review the output.")

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")