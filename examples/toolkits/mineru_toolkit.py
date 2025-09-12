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

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import MinerUToolkit
from camel.types import ModelPlatformType, ModelType


def main():
    # Initialize the toolkit
    mineru_toolkit = MinerUToolkit()

    print("Example 1: Extracting content from a single URL...")
    try:
        # Extract and wait for results
        result = mineru_toolkit.extract_from_urls(
            urls="https://arxiv.org/pdf/2311.10993.pdf"
        )
        print("\nExtraction completed successfully:")
        print(f"Download URL: {result['full_zip_url']}\n")

    except Exception as e:
        print(f"Extraction failed: {e}\n")

    print("Example 2: Extracting content from multiple URLs...")
    try:
        urls = [
            "https://arxiv.org/pdf/2311.10993.pdf",
            "https://arxiv.org/pdf/2310.07298.pdf",
        ]

        # Batch extract and wait for results
        results = mineru_toolkit.extract_from_urls(urls=urls)

        print("\nBatch extraction completed successfully:")
        for result in results['extract_result']:
            print(f"\nDocument: {result['file_name']}")
            print(f"Download URL: {result['full_zip_url']}")

    except Exception as e:
        print(f"Batch extraction failed: {e}\n")

    print("\nExample 3: Using MinerU with ChatAgent...")
    # TODO: implement this example with loader toolkit to get information from
    # the zip url
    try:
        # Set up the ChatAgent with MinerU capabilities
        sys_msg = (
            "You are a helpful assistant that can extract and analyze "
            "content from documents using MinerU's document extraction. "
            "You can handle PDFs and extract text, formulas, and tables. When "
            "processing documents, inform users that it may take time."
        )

        # Initialize the model with specific configuration
        model = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        )

        # Create the agent with MinerU toolkit
        agent = ChatAgent(
            system_message=sys_msg,
            model=model,
            tools=mineru_toolkit.get_tools(),
        )

        # Example document analysis request
        usr_msg = (
            "Please extract and analyze this research paper,"
            "focusing on mathematical formulas and tables: "
            "https://arxiv.org/pdf/2311.10993.pdf "
        )

        response = agent.step(usr_msg)
        print("\nAgent Response:")
        print(response.msg.content)

    except Exception as e:
        print(f"\nAgent interaction failed: {e}\n")


if __name__ == "__main__":
    main()

"""
Example output:

Example 1: Extracting content from a single URL...

Extraction completed successfully:
Download URL: https://cdn-mineru.openxlab.org.cn/pdf/690a7956-eaaa-4fb2-ad7d-6056d1d4e316.zip

Example 2: Extracting content from multiple URLs...

Batch extraction completed successfully:

Document: 2311.10993.pdf
Download URL: https://cdn-mineru.openxlab.org.cn/pdf/690a7956-eaaa-4fb2-ad7d-6056d1d4e316.zip

Document: 2310.07298.pdf
Download URL: https://cdn-mineru.openxlab.org.cn/pdf/250a3762-406e-4279-aa80-47e5ea934509.zip

Example 3: Using MinerU with ChatAgent...

Agent Response:
The extraction of the research paper has been completed. You can download the
extracted content, including mathematical formulas and tables,
from the following link:

[Download Extracted Content]
(https://cdn-mineru.openxlab.org.cn/pdf/690a7956-eaaa-4fb2-ad7d-6056d1d4e316.zip)

If you need any specific analysis or further assistance with the content,
please let me know!

"""
