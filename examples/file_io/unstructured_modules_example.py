# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========

from camel.file_io.unstructured_io import UnstructuredModules

unstructured_modules = UnstructuredModules()


def parse_file_example():
    # take user_roles.txt as example
    path = 'data/ai_society/user_roles.txt'
    elements = unstructured_modules.parse_file_or_url(path)
    return [" ".join(str(el).split()) for el in elements]


def parse_url_example():
    url = ("https://www.cnn.com/2023/01/30/sport/empire-state-building-green-"
           "philadelphia-eagles-spt-intl/index.html")
    elements = unstructured_modules.parse_file_or_url(url)
    return "\n\n".join([str(el) for el in elements])


def clean_text_example():
    text = "Some dirty text â€™ with extra spaces and – dashes."
    options = {
        'replace_unicode_quotes': {},
        'clean_extra_whitespace': {},
        'clean_dashes': {},
        'clean_non_ascii_chars': {}
    }
    return unstructured_modules.clean_text_data(text, options)


def extract_data_example():
    email_text = "Contact me at example@email.com."
    return unstructured_modules.extract_data_from_text("extract_email_address",
                                                       email_text)


def stage_data_example():
    from unstructured.documents.elements import (
        ElementMetadata,
        NarrativeText,
        Title,
    )
    metadata = ElementMetadata(filename="fox.epub")
    elements = [
        Title("A Wonderful Story About A Fox", metadata=metadata),
        NarrativeText(
            "A fox ran into the chicken coop and the chickens flew off!",
            metadata=metadata,
        ),
    ]
    rows = unstructured_modules.stage_elements("stage_for_baseplate", elements)
    return rows


def chunk_url_content_example():
    url = ("https://www.cnn.com/2023/01/30/sport/empire-state-building-green-"
           "philadelphia-eagles-spt-intl/index.html")
    elements = unstructured_modules.parse_file_or_url(url)
    chunks = unstructured_modules.chunk_elements("chunk_by_title", elements)
    return chunks


def main():

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
        print("\n You have parsed data/ai_society/user_roles.txt!")

    elif choice == '2':
        print("Parsing URL example:")
        print(parse_url_example())
        print("\n You have parsed https://www.cnn.com/2023/01/30/sport/"
              "empire-state-building-green-philadelphia-eagles-spt-"
              "intl/index.html")

    elif choice == '3':
        print("Cleaning text example:")
        print("\n Some dirty text â€™ with extra spaces and – dashes."
              "\n \n into \n")
        print(clean_text_example())

    elif choice == '4':
        print("Extracting email example:")
        print(extract_data_example())
        print("extracted from")
        print("Contact me at example@email.com.")

    elif choice == '5':
        print("Staging data example:")
        print(stage_data_example())

    elif choice == '6':
        print("Chunking URL content example:")
        for chunk in chunk_url_content_example():
            print(chunk)
            print("\n" + "-" * 80)

    else:
        print("Invalid choice.")


if __name__ == "__main__":
    main()
