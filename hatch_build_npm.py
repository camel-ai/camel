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
# !/usr/bin/env python3
"""
Hatch build hook for building TypeScript dependencies in
hybrid_browser_toolkit.

This script runs during package building to compile TypeScript code.
It gracefully handles cases where Node.js/npm is not available.
"""

import subprocess
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class NpmBuildHook(BuildHookInterface):
    """Hatch build hook for TypeScript compilation."""

    PLUGIN_NAME = "npm-build"

    def initialize(self, version, build_data):
        """Initialize the build hook and run npm build."""
        self.build_npm_dependencies()

    def finalize(self, version, build_data, artifact_path):
        """Finalize the build - ensure TypeScript was built."""
        base_dir = Path(self.root)
        ts_dir = (
            base_dir / "camel" / "toolkits" / "hybrid_browser_toolkit" / "ts"
        )
        dist_dir = ts_dir / "dist"

        if dist_dir.exists():
            print(f"TypeScript build artifacts found at: {dist_dir}")
        else:
            print("Warning: TypeScript build artifacts not found")

    def build_npm_dependencies(self):
        """Build TypeScript dependencies during wheel/sdist creation."""
        base_dir = Path(self.root)
        ts_dir = (
            base_dir / "camel" / "toolkits" / "hybrid_browser_toolkit" / "ts"
        )

        print(f"Checking TypeScript directory: {ts_dir}")

        if not ts_dir.exists():
            print("TypeScript directory not found, skipping npm build")
            return

        # Check if dist already exists and is not empty
        dist_dir = ts_dir / "dist"
        if dist_dir.exists() and any(dist_dir.iterdir()):
            print(
                "TypeScript already built (dist directory exists), "
                "skipping build"
            )
            return

        try:
            # Check if npm is available
            result = subprocess.run(
                ["npm", "--version"],
                check=True,
                capture_output=True,
                text=True,
            )
            print(f"Found npm version: {result.stdout.strip()}")

            # Check if Node.js is available
            result = subprocess.run(
                ["node", "--version"],
                check=True,
                capture_output=True,
                text=True,
            )
            print(f"Found Node.js version: {result.stdout.strip()}")

            print("Installing npm dependencies...")
            # Use npm install to ensure
            # devDependencies like TypeScript are installed
            subprocess.run(
                ["npm", "install"], cwd=ts_dir, check=True, text=True
            )

            print("Building TypeScript...")
            subprocess.run(
                ["npm", "run", "build"], cwd=ts_dir, check=True, text=True
            )

            # Verify build output
            index_js = dist_dir / "index.js"
            if index_js.exists():
                print("TypeScript build completed successfully")
            else:
                print(
                    "Warning: TypeScript build may have failed (index.js "
                    "not found)"
                )

        except FileNotFoundError:
            print("Warning: npm or node not found in PATH")
            print("Installing without TypeScript support")
            print(
                "To use hybrid_browser_toolkit, please install Node.js and "
                "run:"
            )
            print(f"  cd {ts_dir}")
            print("  npm install && npm run build")

        except subprocess.CalledProcessError as e:
            print(f"Warning: TypeScript build failed with error: {e}")
            print("Installing without TypeScript support")
            print("This may affect hybrid_browser_toolkit functionality")

        except Exception as e:
            print(f"Warning: Unexpected error during TypeScript build: {e}")
            print("Installing without TypeScript support")


def build_npm_dependencies_standalone():
    """Standalone function for testing purposes."""
    base_dir = Path(__file__).parent
    ts_dir = base_dir / "camel" / "toolkits" / "hybrid_browser_toolkit" / "ts"

    print(f"Checking TypeScript directory: {ts_dir}")

    if not ts_dir.exists():
        print("TypeScript directory not found, skipping npm build")
        return

    # Check if dist already exists and is not empty
    dist_dir = ts_dir / "dist"
    if dist_dir.exists() and any(dist_dir.iterdir()):
        print(
            "TypeScript already built (dist directory exists), skipping "
            "build"
        )
        return

    try:
        # Check if npm is available
        result = subprocess.run(
            ["npm", "--version"], check=True, capture_output=True, text=True
        )
        print(f"Found npm version: {result.stdout.strip()}")

        # Check if Node.js is available
        result = subprocess.run(
            ["node", "--version"], check=True, capture_output=True, text=True
        )
        print(f"Found Node.js version: {result.stdout.strip()}")

        print("Installing npm dependencies...")
        # Use npm install to ensure
        # devDependencies like TypeScript are installed
        subprocess.run(["npm", "install"], cwd=ts_dir, check=True, text=True)

        print("Building TypeScript...")
        subprocess.run(
            ["npm", "run", "build"], cwd=ts_dir, check=True, text=True
        )

        # Verify build output
        index_js = dist_dir / "index.js"
        if index_js.exists():
            print("TypeScript build completed successfully")
        else:
            print(
                "Warning: TypeScript build may have failed (index.js not "
                "found)"
            )

    except FileNotFoundError:
        print("Warning: npm or node not found in PATH")
        print("Installing without TypeScript support")
        print("To use hybrid_browser_toolkit, please install Node.js and run:")
        print(f"  cd {ts_dir}")
        print("  npm install && npm run build")

    except subprocess.CalledProcessError as e:
        print(f"Warning: TypeScript build failed with error: {e}")
        print("Installing without TypeScript support")
        print("This may affect hybrid_browser_toolkit functionality")

    except Exception as e:
        print(f"Warning: Unexpected error during TypeScript build: {e}")
        print("Installing without TypeScript support")


if __name__ == "__main__":
    print("=" * 60)
    print("Running Hatch build hook for TypeScript dependencies")
    print("=" * 60)

    build_npm_dependencies_standalone()

    print("=" * 60)
    print("Build hook completed")
    print("=" * 60)
