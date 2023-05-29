# Copyright 2023 @ CAMEL-AI.org. All Rights Reserved.
#
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
# ============================================================================
import os
import re
import sys


def update_license_in_file(file_path: str, license_template_path: str) -> bool:
    with open(file_path, 'r') as f:
        content = f.read()

    with open(license_template_path, 'r') as f:
        new_license = f.read().strip()

    # License always starts with a comment (#)
    # and end with a line of equal signs (===)
    existing_licenses = re.findall(r'^#.*?(?=\n)', content,
                                   re.MULTILINE | re.DOTALL)
    if existing_licenses:
        old_licenses = '\n'.join(existing_licenses)
        if old_licenses.strip() != new_license.strip():
            replaced_content = content.replace(old_licenses, new_license)
            with open(file_path, 'w') as f:
                f.write(replaced_content)
            print(f'Replaced license in {file_path}')
            return True
        else:
            print(f'License already up to date in {file_path}')
    else:
        with open(file_path, 'w') as f:
            f.write(new_license + '\n' + content)
        print(f'Added license to {file_path}')
        return True

    return False


def update_license_in_directory(directory_path: str,
                                license_template_path: str) -> None:
    # Check if directory exists
    if not os.path.isdir(directory_path):
        raise NotADirectoryError(f'{directory_path} is not a directory')
    # Check if license template exists
    if not os.path.isfile(license_template_path):
        raise FileNotFoundError(f'{license_template_path} not found')

    file_count = 0
    for root, _, files in os.walk(directory_path):
        for file_name in files:
            if file_name.endswith('.py'):
                file_path = os.path.join(root, file_name)
                if update_license_in_file(file_path, license_template_path):
                    file_count += 1

    print(f'Licensed update in {file_count} files')


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(
            "Usage: "
            "python update_license.py <directory_path> <license_template_path>"
        )
        directory_path = input("Enter directory path: ")
        license_template_path = input("Enter license template path: ")
    else:
        directory_path = sys.argv[1]
        license_template_path = sys.argv[2]

    update_license_in_directory(directory_path, license_template_path)
