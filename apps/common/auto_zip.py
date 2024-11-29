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
import json
import os
import zipfile


class AutoZip:
    def __init__(self, zip_path: str, ext: str = ".json"):
        self.zip_path = zip_path
        self.zip = zipfile.ZipFile(zip_path, "r")
        self.fl = [f for f in self.zip.filelist if f.filename.endswith(ext)]

    def __next__(self):
        if self.index >= len(self.fl):
            raise StopIteration
        else:
            finfo = self.fl[self.index]
            with self.zip.open(finfo) as f:
                raw_json = json.loads(f.read().decode("utf-8"))
            self.index += 1
            return raw_json

    def __len__(self):
        return len(self.fl)

    def __iter__(self):
        self.index = 0
        return self

    def as_dict(self, include_zip_name: bool = False):
        d = dict()
        for finfo in self.fl:
            with self.zip.open(finfo) as f:
                raw_text = f.read().decode("utf-8")
            if include_zip_name:
                key = os.path.split(self.zip_path)[1] + "/" + finfo.filename
            else:
                key = finfo.filename
            d[key] = raw_text
        return d
