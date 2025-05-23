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
from camel.toolkits.file_write_toolkit import FileWriteToolkit

# Initialize the toolkit
toolkit = FileWriteToolkit(output_dir="./")

# Create a sample presentation content with improved structure
presentation_content = [
    {
        "title": "FileWriteToolkit Presentation",
        "subtitle": "Created with FileWriteToolkit",
    },
    {
        "title": "Key Features",
        "text": ''' Professional Typography\n
          Consistent Styling\n
          Image Integration\n
          Clean Layout''',
        "image": "https://images.pexels.com/photos/1181671/pexels-photo-1181671.jpeg",
    },
    {
        "title": "Design Elements",
        "text": ''' Modern Font Selection\n
          Balanced Color Scheme\n
          Proper Spacing\n
          Responsive Layout''',
        "image": "https://images.pexels.com/photos/1181672/pexels-photo-1181672.jpeg",
    },
    {
        "title": "Implementation",
        "text": ''' Easy to Use\n
          Flexible Structure\n
          Error Handling\n
          Professional Output''',
        "image": "https://images.pexels.com/photos/1181673/pexels-photo-1181673.jpeg",
    },
]

# Write the presentation to a file
result = toolkit._write_pptx_file(
    content=presentation_content, file_path="modern_presentation.pptx"
)

print(result)
