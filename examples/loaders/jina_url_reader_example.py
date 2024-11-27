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


from camel.loaders import JinaURLReader
from camel.types.enums import JinaReturnFormat


def read_with_different_format(return_format, json_response):
    URL = "https://en.wikipedia.org/wiki/Miss_Meyers"
    jina_url_reader = JinaURLReader(
        return_format=return_format, json_response=json_response
    )
    content = jina_url_reader.read_content(URL)
    print(content)


def main():
    formats = [
        JinaReturnFormat.DEFAULT,
        JinaReturnFormat.TEXT,
        JinaReturnFormat.HTML,
        JinaReturnFormat.MARKDOWN,
    ]

    print("Choose a return format of read content:")
    print("1. Default, optimized for LLM inputs")
    print("2. Pure Text")
    print("3. HTML")
    print("4. Markdown")
    choice = input("Enter your choice (1-4): ")

    if not choice.isnumeric() or int(choice) < 1 or int(choice) > 4:
        print("Invalid choice. Exiting.")
        return

    return_format = formats[int(choice) - 1]

    json_response = input("Do you want the response in JSON format? (y/N): ")
    json_response = json_response.lower() == "y"

    read_with_different_format(return_format, json_response)


if __name__ == "__main__":
    main()
