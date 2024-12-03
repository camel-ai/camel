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

from camel.loaders.unstructured_io import UnstructuredIO

unstructured_modules = UnstructuredIO()


def parse_file_example():
    with open("mydoc.txt", "w") as file:
        # Writing content to the file
        file.write("Important Analysis\n")
        file.write("\n")
        file.write("Here is my first thought.\n")
        file.write("\n")
        file.write("Here is my second thought.\n")

    elements = unstructured_modules.parse_file_or_url("mydoc.txt")
    content = "\n\n".join([str(el) for el in elements])
    # Cleanup: remove the created file after the example
    if os.path.exists("mydoc.txt"):
        os.remove("mydoc.txt")
    return content


def parse_url_example(url):
    elements = unstructured_modules.parse_file_or_url(url)
    content = "\n\n".join([str(el) for el in elements])
    return content


def clean_text_example(text):
    options = [
        ('replace_unicode_quotes', {}),
        ('clean_dashes', {}),
        ('clean_non_ascii_chars', {}),
        ('clean_extra_whitespace', {}),
    ]
    return unstructured_modules.clean_text_data(
        text=text, clean_options=options
    )


def extract_data_example(text):
    return unstructured_modules.extract_data_from_text(
        text=text, extract_type="extract_email_address"
    )


def stage_data_example(url):
    elements = unstructured_modules.parse_file_or_url(url)

    staged_element = unstructured_modules.stage_elements(
        elements=elements, stage_type="stage_for_baseplate"
    )
    return staged_element


def chunk_url_content_example(url):
    elements = unstructured_modules.parse_file_or_url(url)
    chunks = unstructured_modules.chunk_elements(
        elements=elements, chunk_type="chunk_by_title"
    )
    return chunks


def main():
    example_url = (
        "https://www.cnn.com/2023/01/30/sport/empire-state-building-green-"
        "philadelphia-eagles-spt-intl/index.html"
    )
    example_dirty_text = (
        "\x93Some dirty text â€™ with extra spaces and – dashes."  # noqa: RUF001
    )
    example_email_text = "Contact me at example@email.com."

    print("Choose an example to run:")
    print("1. Parse File")
    print("2. Parse URL")
    print("3. Clean Text")
    print("4. Extract Data")
    print("5. Stage Data")
    print("6. Chunk URL Content")
    choice = input("Enter your choice (1-6): ")

    if choice == '1':
        print("Parsing file example:")
        print(parse_file_example())

    elif choice == '2':
        print("Parsing URL example:")
        print(parse_url_example(example_url))

    elif choice == '3':
        print("Cleaning text example:")
        print(example_dirty_text)
        print(clean_text_example(example_dirty_text))

    elif choice == '4':
        print("Extracting email example:")
        print(extract_data_example(example_email_text))
        print("extracted from")
        print(example_email_text)

    elif choice == '5':
        print("Staging data example:")
        print(stage_data_example(example_url))

    elif choice == '6':
        print("Chunking URL content example:")
        for chunk in chunk_url_content_example(example_url):
            print(chunk)
            print("\n" + "-" * 80)

    else:
        print("Invalid choice.")


if __name__ == "__main__":
    main()
