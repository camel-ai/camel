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
"""
Hatch build hook for building TypeScript dependencies in
hybrid_browser_toolkit.

This script runs during package building to compile TypeScript code.
It gracefully handles cases where Node.js/npm is not available.
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Optional, Tuple

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class NpmBuildHook(BuildHookInterface):
    r"""Hatch build hook for TypeScript compilation."""

    PLUGIN_NAME = "npm-build"

    def initialize(self, version, build_data):
        r"""Initialize the build hook and run npm build."""
        self.build_npm_dependencies()

    def finalize(self, version, build_data, artifact_path):
        r"""Finalize the build - ensure TypeScript was built."""
        base_dir = Path(self.root)
        ts_dir = self._get_ts_directory(base_dir)
        dist_dir = ts_dir / "dist"

        if dist_dir.exists():
            print(f"TypeScript build artifacts found at: {dist_dir}")
        else:
            print("Warning: TypeScript build artifacts not found")

    def _get_ts_directory(self, base_dir: Path) -> Path:
        r"""Get the TypeScript directory path."""
        return (
            base_dir / "camel" / "toolkits" / "hybrid_browser_toolkit" / "ts"
        )

    def _parse_version(self, version_str: str) -> Tuple[int, int, int]:
        r"""Parse version string into major, minor, patch numbers."""
        version_str = version_str.strip().lstrip('v')
        match = re.match(r'(\d+)\.(\d+)\.(\d+)', version_str)
        if match:
            return tuple(map(int, match.groups()))
        return (0, 0, 0)

    def _check_version_requirement(self, current: str, required: str) -> bool:
        r"""Check if current version meets requirement."""
        if required.startswith('>='):
            required_version = self._parse_version(required[2:])
            current_version = self._parse_version(current)
            return current_version >= required_version
        elif required.startswith('^'):
            required_version = self._parse_version(required[1:])
            current_version = self._parse_version(current)
            return (
                current_version[0] == required_version[0]
                and current_version >= required_version
            )
        return True

    def _get_package_requirements(self, ts_dir: Path) -> Optional[dict]:
        r"""Get Node.js/npm version requirements from package.json or
        package-lock.json.
        """
        package_json = ts_dir / "package.json"
        package_lock = ts_dir / "package-lock.json"

        try:
            if package_json.exists():
                with open(package_json, 'r') as f:
                    data = json.load(f)
                    if 'engines' in data:
                        return data['engines']

            if package_lock.exists():
                with open(package_lock, 'r') as f:
                    data = json.load(f)
                    for pkg_name, pkg_data in data.get('packages', {}).items():
                        if not pkg_name and 'engines' in pkg_data:
                            return pkg_data['engines']

        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not read package requirements: {e}")

        return None

    def _check_node_npm_versions(
        self, ts_dir: Path
    ) -> Tuple[Optional[str], Optional[str], bool]:
        r"""Check Node.js and npm versions against requirements."""
        node_version = None
        npm_version = None
        versions_ok = True

        try:
            result = subprocess.run(
                ["node", "--version"],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            node_version = result.stdout.strip()
            print(f"Found Node.js version: {node_version}")
        except (FileNotFoundError, subprocess.CalledProcessError):
            print("Warning: Node.js not found in PATH")
            return None, None, False

        try:
            result = subprocess.run(
                ["npm", "--version"],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            npm_version = result.stdout.strip()
            print(f"Found npm version: {npm_version}")
        except (FileNotFoundError, subprocess.CalledProcessError):
            print("Warning: npm not found in PATH")
            return node_version, None, False

        requirements = self._get_package_requirements(ts_dir)
        if requirements:
            if 'node' in requirements:
                node_req = requirements['node']
                if not self._check_version_requirement(node_version, node_req):
                    print(
                        f"Warning: Node.js version {node_version} "
                        f"does not meet requirement {node_req}"
                    )
                    versions_ok = False
                else:
                    print(
                        f"✓ Node.js version {node_version} meets "
                        f"requirement {node_req}"
                    )

            if 'npm' in requirements:
                npm_req = requirements['npm']
                if not self._check_version_requirement(npm_version, npm_req):
                    print(
                        f"Warning: npm version {npm_version} does not "
                        f"meet requirement {npm_req}"
                    )
                    versions_ok = False
                else:
                    print(
                        f"✓ npm version {npm_version} meets "
                        f"requirement {npm_req}"
                    )

        return node_version, npm_version, versions_ok

    def _run_npm_build_process(self, ts_dir: Path, dist_dir: Path) -> bool:
        r"""Run the npm build process."""
        try:
            print("Installing npm dependencies...")
            subprocess.run(
                ["npm", "install"],
                cwd=ts_dir,
                check=True,
                text=True,
                timeout=300,
            )

            print("Building TypeScript...")
            subprocess.run(
                ["npm", "run", "build"],
                cwd=ts_dir,
                check=True,
                text=True,
                timeout=300,
            )

            print("Installing Playwright browsers...")
            try:
                subprocess.run(
                    ["npx", "playwright", "install"],
                    cwd=ts_dir,
                    check=True,
                    text=True,
                    timeout=600,
                )
                print("Playwright browsers installed successfully")
            except subprocess.CalledProcessError as e:
                print(f"Warning: Playwright browser installation failed: {e}")
                print(
                    "Users will need to run 'npx playwright install' manually"
                )
                print("  npx playwright install")

            index_js = dist_dir / "index.js"
            if index_js.exists():
                print("TypeScript build completed successfully")
                return True
            else:
                print(
                    "Warning: TypeScript build may have failed (index.js "
                    "not found)"
                )
                return False

        except subprocess.CalledProcessError as e:
            print(f"Warning: TypeScript build failed with error: {e}")
            print("Installing without TypeScript support")
            print("This may affect hybrid_browser_toolkit functionality")
            return False

        except Exception as e:
            print(f"Warning: Unexpected error during TypeScript build: {e}")
            print("Installing without TypeScript support")
            return False

    def _print_manual_instructions(self, ts_dir: Path):
        r"""Print manual installation instructions."""
        print("Installing without TypeScript support")
        print("To use hybrid_browser_toolkit, please install Node.js and run:")
        print(f"  cd {ts_dir}")
        print("  npm install && npm run build")
        print("  npx playwright install")

    def build_npm_dependencies(self):
        r"""Build TypeScript dependencies during wheel/sdist creation."""
        base_dir = Path(self.root)
        ts_dir = self._get_ts_directory(base_dir)

        print(f"Checking TypeScript directory: {ts_dir}")

        if not ts_dir.exists():
            print("TypeScript directory not found, skipping npm build")
            return

        dist_dir = ts_dir / "dist"
        if dist_dir.exists() and any(dist_dir.iterdir()):
            print(
                "TypeScript already built (dist directory exists), "
                "skipping build"
            )
            return

        node_version, npm_version, versions_ok = self._check_node_npm_versions(
            ts_dir
        )

        if node_version is None or npm_version is None:
            print("Warning: npm or node not found in PATH")
            self._print_manual_instructions(ts_dir)
            return

        if not versions_ok:
            print("Warning: Node.js/npm version requirements not met")
            print("Continuing anyway, but build may fail")

        self._run_npm_build_process(ts_dir, dist_dir)


def build_npm_dependencies_standalone():
    r"""Standalone function for testing purposes."""
    hook = NpmBuildHook(None, None)
    hook.root = Path(__file__).parent.absolute()
    hook.build_npm_dependencies()


if __name__ == "__main__":
    print("=" * 60)
    print("Running Hatch build hook for TypeScript dependencies")
    print("=" * 60)

    build_npm_dependencies_standalone()

    print("=" * 60)
    print("Build hook completed")
    print("=" * 60)
