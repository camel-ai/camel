#!/usr/bin/env python

####################
# The code here is used to download data for alfworld
# File taken from https://github.com/alfworld/alfworld/blob/master/scripts/alfworld-download
# the original copy was provided under MIT license.
# If you are unable to use this copy, then you have to
####################

import os
import shutil
import zipfile
import argparse
import requests
import tempfile
from os.path import join as pjoin

from tqdm import tqdm

from alfworld.utils import mkdirs


JSON_FILES_URL = "https://github.com/alfworld/alfworld/releases/download/0.2.2/json_2.1.1_json.zip"
PDDL_FILES_URL = "https://github.com/alfworld/alfworld/releases/download/0.2.2/json_2.1.1_pddl.zip"
TW_PDDL_FILES_URL = "https://github.com/alfworld/alfworld/releases/download/0.2.2/json_2.1.1_tw-pddl.zip"
MRCNN_URL = "https://github.com/alfworld/alfworld/releases/download/0.2.2/mrcnn_alfred_objects_sep13_004.pth"
CHECKPOINTS_URL = "https://github.com/alfworld/alfworld/releases/download/0.2.2/pretrained_checkpoints.zip"
SEQ2SEQ_DATA_URL = "https://github.com/alfworld/alfworld/releases/download/0.2.2/seq2seq_data.zip"


def download(url, dst, force=False):
    """ Download a remote file using HTTP get request.

    Args:
        url (str): URL where to get the file.
        dst (str): Destination folder where to save the file.
        force (bool, optional):
            Download again if it exists]. Defaults to False.

    Returns:
        str: Path to the downloaded file.

    Notes:
        This code is inspired by
        https://github.com/huggingface/transformers/blob/v4.0.0/src/transformers/file_utils.py#L1069
    """
    filename = url.split('/')[-1]
    path = pjoin(mkdirs(dst), filename)

    if os.path.isfile(path) and not force:
        return path

    # Download to a temp folder first to avoid corrupting the cache
    # with incomplete downloads.
    temp_dir = mkdirs(pjoin(tempfile.gettempdir(), "alfworld"))
    temp_path = pjoin(temp_dir, filename)
    with open(temp_path, 'ab') as temp_file:
        headers = {}
        resume_size = temp_file.tell()
        if resume_size:
            headers['Range'] = f'bytes={resume_size}-'
            headers['x-ms-version'] = "2020-04-08"  # Needed for Range support.

        r = requests.get(url, stream=True, headers=headers)
        if r.headers.get("x-ms-error-code") == "InvalidRange" and r.headers["Content-Range"].rsplit("/", 1)[-1] == str(resume_size):
            shutil.move(temp_path, path)
            return path

        r.raise_for_status()  # Bad request.
        content_length = r.headers.get("Content-Length")
        total = resume_size + int(content_length)
        pbar = tqdm(
            unit="B",
            initial=resume_size,
            unit_scale=True,
            total=total,
            desc="Downloading {}".format(filename),
        )

        for chunk in r.iter_content(chunk_size=1024):
            if chunk:  # filter out keep-alive new chunks
                pbar.update(len(chunk))
                temp_file.write(chunk)

    shutil.move(temp_path, path)

    pbar.close()
    return path


def unzip(filename, dst, force=False):
    zipped_file = zipfile.ZipFile(filename)
    filenames_to_extract = list(zipped_file.namelist())

    desc = f"Extracting {os.path.basename(filename)}"
    skipped = 0
    for f in tqdm(filenames_to_extract, desc=desc):
        if not os.path.isfile(pjoin(dst, f)) or force:
            zipped_file.extract(f, dst)
        else:
            skipped += 1

    if skipped:
        print(f"{skipped} files skipped (use -f to overwrite).")


def build_argparser():

    parser = argparse.ArgumentParser()

    parser.add_argument("--data-dir", default=ALFWORLD_DATA,
                        help="Folder where to download the data. Default: '%(default)s'")
    parser.add_argument("--extra", action="store_true",
                        help="Also, download pre-trained BUTLER agents and Seq2Seq training files.")
    parser.add_argument("-f", "--force", action="store_true",
                        help="Overwrite existing files.")
    parser.add_argument("-ff", "--force-download", action="store_true",
                        help="Download data again.")

    return parser


def download_alfworld_data(data_dir=None, extra=False, force=False, force_download=False):

    from alfworld.info import ALFWORLD_DATA
    from alfworld.info import ALFRED_PDDL_PATH, ALFRED_TWL2_PATH

    if data_dir is None:
        data_dir = ALFWORLD_DATA
    print(f"Data directory where we will download ALFWORLD data is {data_dir}")

    # parser = build_argparser()
    # args = parser.parse_args()

    zipped_filename = download(JSON_FILES_URL, dst=data_dir,
                               force=force_download)
    unzip(zipped_filename, dst=data_dir, force=force)
    os.remove(zipped_filename)

    zipped_filename = download(PDDL_FILES_URL, dst=data_dir,
                               force=force_download)
    unzip(zipped_filename, dst=data_dir, force=force)
    os.remove(zipped_filename)

    zipped_filename = download(TW_PDDL_FILES_URL, dst=data_dir,
                               force=force_download)
    unzip(zipped_filename, dst=data_dir, force=force)
    os.remove(zipped_filename)

    download(MRCNN_URL, dst=pjoin(data_dir, "detectors"), force=force_download)

    if extra:
        zipped_filename = download(CHECKPOINTS_URL, dst=data_dir, force=force_download)
        unzip(zipped_filename, dst=pjoin(data_dir, "agents"), force=force)
        os.remove(zipped_filename)

        zipped_filename = download(SEQ2SEQ_DATA_URL, dst=data_dir, force=force_download)
        unzip(zipped_filename, dst=data_dir, force=force)
        os.remove(zipped_filename)

    # Get a copy of the PDDL and TW logic files.
    logic_dir = mkdirs(pjoin(data_dir, "logic"))
    alfred_pddl_path = pjoin(logic_dir, "alfred.pddl")
    if not os.path.isfile(alfred_pddl_path) or force:
        shutil.copy(ALFRED_PDDL_PATH, alfred_pddl_path)
    else:
        print(f"{alfred_pddl_path} already exists (use -f to overwrite).")

    alfred_twl2_path = pjoin(logic_dir, "alfred.twl2")
    if not os.path.isfile(alfred_twl2_path) or force:
        shutil.copy(ALFRED_TWL2_PATH, alfred_twl2_path)
    else:
        print(f"{alfred_twl2_path} already exists (use -f to overwrite).")


if __name__ == "__main__":
    download_alfworld_data()
