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

from camel.loaders import MarkItDownConverter

# Create mock files for testing
mock_files = {
    "demo.html": "<html><body><h1>Demo HTML</h1></body></html>",
    "report.pdf": "%PDF-1.4\n% Mock PDF content",
    "presentation.pptx": "Mock PPTX content",
    "data.xlsx": "Mock XLSX content",
}

# Write mock files to disk
for filename, content in mock_files.items():
    with open(filename, "w") as f:
        f.write(content)


converter = MarkItDownConverter()

# Convert a single file
try:
    markdown_text = converter.convert_file("demo.html")
    print(markdown_text)
except Exception as e:
    print(f"An error occurred: {e}")

# Convert multiple files
files = ["report.pdf", "presentation.pptx", "data.xlsx"]
converted = converter.convert_files(files)
for path, md in converted.items():
    print(f"Markdown for {path}:\n{md}\n")

# Clean up mock files
for filename in mock_files.keys():
    os.remove(filename)
