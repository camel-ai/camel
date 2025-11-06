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
import tempfile

from camel.loaders import MarkItDownLoader

mock_files = {
    "demo.html": "<html><body><h1>Demo HTML</h1></body></html>",
    "report.pdf": "%PDF-1.4\n% Mock PDF content",
    "presentation.pptx": "Mock PPTX content",
    "data.xlsx": "Mock XLSX content",
}

with tempfile.TemporaryDirectory() as temp_dir:
    file_paths = {}

    for filename, content in mock_files.items():
        file_path = os.path.join(temp_dir, filename)
        with open(file_path, "w") as f:
            f.write(content)
        file_paths[filename] = file_path

    converter = MarkItDownLoader()

    # Convert a single file
    try:
        markdown_text = converter.convert_file(file_paths["demo.html"])
        print(markdown_text)
    except Exception as e:
        print(f"An error occurred: {e}")

    # Convert multiple files
    files = [
        file_paths["report.pdf"],
        file_paths["presentation.pptx"],
        file_paths["data.xlsx"],
    ]
    converted = converter.convert_files(files, parallel=True, skip_failed=True)
    for path, md in converted.items():
        print(f"Markdown for {path}:\n{md}\n")

"""
===============================================================================
# Demo HTML
Markdown for /var/folders/93/f_71_t957cq9cmq2gsybs4_40000gn/T/tmp86hqcsxc/
report.pdf:
%PDF-1.4
% Mock PDF content

Markdown for /var/folders/93/f_71_t957cq9cmq2gsybs4_40000gn/T/tmp86hqcsxc/data.
xlsx:
Mock XLSX content

Markdown for /var/folders/93/f_71_t957cq9cmq2gsybs4_40000gn/T/tmp86hqcsxc/
presentation.pptx:
===============================================================================
"""
