import os
import urllib.request

from huggingface_hub import hf_hub_download
from huggingface_hub.utils._errors import RepositoryNotFoundError

REPO_ROOT = os.path.realpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))


def download_data():

    print("Downloading...")

    data_dir = os.path.join(REPO_ROOT, "datasets/")

    os.makedirs(data_dir, exist_ok=True)

    try:
        hf_hub_download(repo_id="camel-ai/ai_society", repo_type="dataset",
                        filename="ai_society_chat.zip", local_dir=data_dir,
                        local_dir_use_symlinks=False)

        hf_hub_download(repo_id="camel-ai/code", repo_type="dataset",
                        filename="code_chat.zip", local_dir=data_dir,
                        local_dir_use_symlinks=False)
    except RepositoryNotFoundError:
        for name in ("ai_society_chat.zip", "code_chat.zip"):
            data_url = ("https://storage.googleapis.com/"
                        f"camel-bucket/datasets/private/{name}")
            file_path = os.path.join(data_dir, os.path.split(data_url)[1])
            urllib.request.urlretrieve(data_url, file_path)

    data_url = ("https://storage.googleapis.com/"
                "camel-bucket/datasets/private/misalignment.zip")
    file_path = os.path.join(data_dir, os.path.split(data_url)[1])
    urllib.request.urlretrieve(data_url, file_path)

    print("Download done")


if __name__ == "__main__":
    download_data()
