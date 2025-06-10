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
import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from logging.handlers import RotatingFileHandler
from queue import Empty, Queue
from threading import Thread

import requests


def setup_dispatcher_logging():
    log_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
    log_file = 'dispatcher.log'

    logger = logging.getLogger('dispatcher')
    logger.setLevel(logging.INFO)

    # File Handler
    file_handler = RotatingFileHandler(
        log_file, maxBytes=1024 * 1024 * 5, backupCount=2
    )
    file_handler.setFormatter(log_formatter)
    logger.addHandler(file_handler)

    # Stream Handler (for console output)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(log_formatter)
    logger.addHandler(stream_handler)

    return logger


log = setup_dispatcher_logging()


def download_website_assets(project_name: str):
    log.info(f"Checking for assets for project: {project_name}")

    # Check if assets already exist
    project_dir = project_name
    templates_path = os.path.join(project_dir, 'templates')
    static_path = os.path.join(project_dir, 'static')
    if os.path.exists(templates_path) and os.path.exists(static_path):
        log.info(
            "Templates and static folders already exist. Skipping download."
        )
        return True

    log.info(f"Attempting to download assets for project: {project_name}")
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        log.error(
            "huggingface_hub not installed. "
            "Please install it with `pip install huggingface-hub`"
        )
        return False

    repo_id = "camel-ai/mock_websites"
    local_dir_root = "hf_mock_website"
    project_pattern = f"{project_name}/*"

    try:
        # Download only the project's folder
        snapshot_path = snapshot_download(
            repo_id=repo_id,
            repo_type="dataset",
            allow_patterns=project_pattern,
            local_dir=local_dir_root,
            local_dir_use_symlinks=False,
            # Use False for Windows compatibility
        )
        log.info(f"Snapshot downloaded to: {snapshot_path}")

        # The downloaded content for the project is in a subdirectory
        project_assets_path = os.path.join(snapshot_path, project_name)

        if not os.path.isdir(project_assets_path):
            log.error(
                f"Project folder '{project_name}' not found in downloaded "
                f"assets at '{project_assets_path}'"
            )
            return False

        # Copy templates and static folders into project root
        for folder in ['templates', 'static']:
            src = os.path.join(project_assets_path, folder)
            # Destination is now inside the project folder
            dst = os.path.join(".", project_name, folder)
            if not os.path.exists(src):
                log.warning(f"'{src}' not found in downloaded assets.")
                continue

            if os.path.exists(dst):
                log.info(f"Removing existing '{dst}' directory.")
                shutil.rmtree(dst)
            log.info(f"Copying '{src}' to '{dst}'.")
            shutil.copytree(src, dst)
        log.info(f"Assets for '{project_name}' are set up.")
        return True
    except Exception as e:
        log.error(f"Failed to download or set up assets: {e}")
        return False


def enqueue_output(stream, queue):
    # If `stream` is from a subprocess opened with `text=True`,
    # then `readline()` returns strings, and `''` is the sentinel for EOF.
    for line in iter(stream.readline, ''):
        queue.put(line)
    stream.close()


def run_project(project_name: str, port: int):
    # 1. Prepare environment
    log.info(f"Setting up project: {project_name}")
    if not download_website_assets(project_name):
        log.error("Failed to download assets. Aborting.")
        return

    # Load task configuration
    task_file = 'task.json'
    if not os.path.exists(task_file):
        log.error(f"'{task_file}' not found. Aborting.")
        return
    with open(task_file, 'r') as f:
        task_data = json.load(f)
    products = task_data.get("products", [])
    ground_truth = task_data.get("ground_truth_cart", [])

    # Prepare project-specific files
    project_dir = project_name
    app_path = os.path.join(project_dir, 'app.py')
    if not os.path.exists(app_path):
        log.error(f"Application file not found: {app_path}. Aborting.")
        return

    # Write the products to a file inside the project directory
    with open(os.path.join(project_dir, 'products.json'), 'w') as f:
        json.dump(products, f)
    log.info(f"Wrote products.json to '{project_dir}'.")

    # Start the web server app
    # Use sys.executable to ensure we use the same python interpreter
    cmd = [sys.executable, app_path, '--port', str(port)]
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True,
    )
    log.info(f"Started {app_path} on port {port} with PID: {process.pid}")

    # Non-blocking stream reading for both stdout and stderr
    q_out: Queue[str] = Queue()
    t_out = Thread(target=enqueue_output, args=(process.stdout, q_out))
    t_out.daemon = True
    t_out.start()

    q_err: Queue[str] = Queue()
    t_err = Thread(target=enqueue_output, args=(process.stderr, q_err))
    t_err.daemon = True
    t_err.start()

    time.sleep(5)  # Wait for server to start

    # 5. Start the task and then wait for user to terminate
    base_url = f"http://127.0.0.1:{port}"
    try:
        # Start task
        log.info(f"Starting task with ground truth: {ground_truth}")
        r = requests.post(
            f"{base_url}/task/start", json={"ground_truth_cart": ground_truth}
        )
        r.raise_for_status()
        log.info(f"Task started on server: {r.json()['message']}")
        print(
            "Server is running. Interact with the website at "
            f"http://127.0.0.1:{port}"
        )
        print("Dispatcher is now polling for task completion...")
        print("Press Ctrl+C to stop the dispatcher early and get results.")

        # Poll for task completion
        while True:
            # Check if the subprocess has terminated unexpectedly
            if process.poll() is not None:
                log.error("App process terminated unexpectedly.")
                break

            # Check for completion via API
            try:
                r_check = requests.get(f"{base_url}/task/check")
                r_check.raise_for_status()
                status = r_check.json()
                if status.get('completed', False):
                    log.info(
                        "Task completion reported by API. "
                        "Proceeding to final report and shutdown."
                    )
                    break  # Exit the loop on completion
            except requests.exceptions.RequestException as e:
                log.error(f"Could not poll task status: {e}")
                break  # Exit if the server becomes unresponsive

            # Log any error output from the app
            try:
                err_line = q_err.get_nowait()
                log.error(f"APP STDERR: {err_line.strip()}")
            except Empty:
                pass  # No new error output
            time.sleep(2)  # Wait for 2 seconds before polling again

    except KeyboardInterrupt:
        log.info(
            "\nCtrl+C detected. Shutting down and checking final task status."
        )

    except requests.exceptions.RequestException as e:
        log.error(f"Failed to communicate with the web app: {e}")
    finally:
        # 6. Check task completion
        log.info("Checking final task completion status.")
        op_steps = 0
        try:
            r = requests.get(f"{base_url}/task/check")
            r.raise_for_status()
            result = r.json()
            log.info(f"Final task check result: {result}")
            success = result.get('completed', False)
            op_steps = result.get('steps', 0)
        except requests.exceptions.RequestException as e:
            log.error(f"Could not get final task status: {e}")
            success = False

        log.info("--- FINAL FEEDBACK ---")
        log.info(f"Project: {project_name}")
        log.info(f"Success: {success}")
        log.info(f"Total Operation Steps: {op_steps}")
        log.info("----------------------")

        # 7. Shutdown server
        log.info("Shutting down web server.")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            log.warning("Server did not terminate gracefully. Killing.")
            process.kill()
        log.info("Web server process stopped.")
        # Log any remaining stderr for debugging
        # Drain the queue first
        while not q_err.empty():
            log.error(f"APP STDERR: {q_err.get_nowait().strip()}")


def main():
    parser = argparse.ArgumentParser(
        description="Dispatcher for running mock website benchmarks."
    )
    parser.add_argument(
        '--project',
        type=str,
        default='shopping_mall',
        help='The name of the project to run (e.g., shopping_mall).',
    )
    parser.add_argument(
        '--port',
        type=int,
        default=5001,
        help='Port to run the project web server on.',
    )
    args = parser.parse_args()

    run_project(args.project, args.port)


if __name__ == "__main__":
    main()
