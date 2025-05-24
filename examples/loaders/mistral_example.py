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

from camel.loaders import MistralReader

mock_files = {
    "report.pdf": "%PDF-1.4\n% Mock PDF content",
}

with tempfile.TemporaryDirectory() as temp_dir:
    file_paths = {}

    for filename, content in mock_files.items():
        file_path = os.path.join(temp_dir, filename)
        with open(file_path, "w") as f:
            f.write(content)
        file_paths[filename] = file_path

    converter = MistralReader()

    try:
        markdown_text = converter.extract_text(file_paths["report.pdf"])
        print(markdown_text)
    except Exception as e:
        print(f"An error occurred: {e}")
