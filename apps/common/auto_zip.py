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
