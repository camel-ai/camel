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
import shutil
import subprocess
from pathlib import Path

SPHINX_SOURCE_DIR = "docs"
SPHINX_BUILD_DIR = "docs/_build/markdown"
MINTLIFY_DOCS_DIR = "mintlify/docs"


def build_sphinx_docs():
    print(
        "📚 Building markdown documentation from reStructuredText using Sphinx"
    )
    subprocess.run(
        [
            "sphinx-build",
            "-b",
            "markdown",
            SPHINX_SOURCE_DIR,
            SPHINX_BUILD_DIR,
        ],
        check=True,
    )
    print("✅ Sphinx docs build complete.")


def copy_markdown_docs():
    print(f"📦 Copying Sphinx-generated .md files to {MINTLIFY_DOCS_DIR}...")
    os.makedirs(MINTLIFY_DOCS_DIR, exist_ok=True)
    for md_file in Path(SPHINX_BUILD_DIR).rglob("*.md"):
        dest_file = Path(MINTLIFY_DOCS_DIR) / md_file.name
        shutil.copy(md_file, dest_file)
    print("✅ Copy complete.")


def rename_md_to_mdx():
    print("🔁 Renaming .md files to .mdx...")
    for md_file in Path(MINTLIFY_DOCS_DIR).glob("*.md"):
        mdx_file = md_file.with_suffix(".mdx")
        md_file.rename(mdx_file)
    print("✅ Rename complete.")


def remove_style_tags():
    print("🧹 Removing <style>...</style> blocks from .mdx files...")
    for mdx_file in Path(MINTLIFY_DOCS_DIR).glob("*.mdx"):
        content = mdx_file.read_text(encoding="utf-8")
        import re

        cleaned = re.sub(
            r"<style[\s\S]*?</style>", "", content, flags=re.IGNORECASE
        )
        mdx_file.write_text(cleaned, encoding="utf-8")
    print("✅ <style> blocks removed.")


def main():
    build_sphinx_docs()
    copy_markdown_docs()
    rename_md_to_mdx()
    remove_style_tags()
    print("🎉 All done! Your Mintlify documentation is ready.")


if __name__ == "__main__":
    main()
