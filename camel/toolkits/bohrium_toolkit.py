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
from typing import Any, Dict, List, Optional

try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import MCPServer, api_keys_required

logger = get_logger(__name__)


@MCPServer()
class BohriumToolkit(BaseToolkit):
    r"""A class representing a toolkit for interacting with Bohrium services.

    Args:
        timeout (Optional[float], optional): The timeout for BohriumToolkit.
           (default: :obj:`None`)
        api_key (Optional[str], optional): The API key for Bohrium client.
           (default: :obj:`None`)
        project_id (Optional[int], optional): The project ID for Bohrium
            client. (default: :obj:`None`)
        yaml_path (Optional[str], optional): The path to the YAML file
            containing the job parameters. (default: :obj:`None`)
    """

    @api_keys_required(
        [
            ("api_key", "BOHRIUM_API_KEY"),
        ]
    )
    def __init__(
        self,
        timeout: Optional[float] = None,
        api_key: Optional[str] = None,
        project_id: Optional[int] = None,
        yaml_path: Optional[str] = None,
        _test_mode: bool = False,  # Used for testing without dependency
    ):
        super().__init__(timeout=timeout)

        # Special path for testing without bohrium installed
        if _test_mode:
            self._client = None
            self._job = None
            self._project_id = project_id
            self._yaml_path = yaml_path
            return

        try:
            # Only import bohrium if not in test mode
            from bohrium._client import Bohrium
            from bohrium.resources import Job
        except ImportError:
            logger.error(
                "bohrium is not installed, install it from "
                "https://github.com/dptech-corp"
                "/bohrium-openapi-python-sdk"
            )
            raise

        api_key = api_key or os.environ.get("BOHRIUM_API_KEY")
        self._client = Bohrium(access_key=api_key, project_id=project_id)
        self._job = Job(self._client)
        self._project_id = project_id
        self._yaml_path = yaml_path

        # refactor insert method
        self._job.insert = self._custom_insert

    def _custom_insert(self, data):
        r"""refactor insert method, ensure return jobId information"""

        response = self._client.post("/openapi/v2/job/add", json=data)
        result = response.json()

        return result

    def submit_job(
        self,
        job_name: str = "bohr-job",
        machine_type: str = "c2_m4_cpu",
        cmd: str = "mpirun -n 2 lmp_mpi -i in.shear",
        image_address: str = "registry.dp.tech/dptech/lammps:29Sep2021",
    ) -> Dict[str, Any]:
        r"""Submit a job to Bohrium.

        Args:
            job_name (str): The name of the job. It will be updated when yaml
                file is provided. The yaml file might be set when initialize
                BohriumToolkit.
                (default: :obj:`bohr-job`)
            machine_type (str): The type of machine to use. It will be updated
                when yaml file is provided. The yaml file might be set when
                initialize BohriumToolkit.
                (default: :obj:`c2_m4_cpu`)
            cmd (str): The command to run. It will be updated when yaml file
                is provided. The yaml file might be set when initialize
                (default: :obj:`mpirun -n 2 lmp_mpi -i in.shear`)
            image_address (str): The address of the image to use. It will be
                updated when yaml file is provided. The yaml file might be set
                when initialize BohriumToolkit.
                (default: :obj:`registry.dp.tech/dptech/lammps:29Sep2021`)

        Returns:
            Dict[str, Any]: The result of the job submission.
        """
        # Initialize params with default values
        params: Dict[str, Any] = {
            "project_id": self._project_id,
            "job_name": job_name,
            "machine_type": machine_type,
            "cmd": cmd,
            "image_address": image_address,
            "work_dir": "",
            "result": "",
            "dataset_path": [],
            "log_files": [],
            "out_files": [],
        }

        # First load from YAML file if provided
        if self._yaml_path and HAS_YAML:
            try:
                with open(self._yaml_path, 'r') as file:
                    yaml_params = yaml.safe_load(file)
                    if yaml_params:
                        params.update(yaml_params)
            except yaml.YAMLError as e:
                logger.error(f"Error parsing YAML file: {e}")
                return {"error": f"YAML parsing error: {e!s}"}
            except FileNotFoundError:
                logger.error(f"YAML file not found: {self._yaml_path}")
                return {"error": f"File not found: {self._yaml_path}"}
            except Exception as e:
                logger.error(f"Error loading YAML file: {e}")
                return {"error": str(e)}
        elif self._yaml_path and not HAS_YAML:
            logger.warning(
                "PyYAML is not installed. YAML file will be ignored."
            )
            return {"warning": "PyYAML is not installed. YAML file ignored."}

        try:
            result = self._job.submit(  # type: ignore[union-attr]
                project_id=params["project_id"],
                job_name=params["job_name"],
                machine_type=params["machine_type"],
                cmd=params["cmd"],
                image_address=params["image_address"],
                job_group_id=params.get("job_group_id", 0),
                work_dir=params["work_dir"],
                result=params["result"],
                dataset_path=params["dataset_path"],
                log_files=params["log_files"],
                out_files=params["out_files"],
            )

            return {"status": "Job submitted successfully", "result": result}

        except Exception as e:
            logger.error(f"Error submitting job: {e}")
            return {"error": str(e)}

    def get_job_details(self, job_id: int) -> Dict[str, Any]:
        r"""Get details for a specific job.

        Args:
            job_id (int): The ID of the job.

        Returns:
            Dict[str, Any]: The job details.
        """
        try:
            return self._job.detail(job_id)  # type: ignore[union-attr]
        except Exception as e:
            logger.error(f"Error getting job details: {e}")
            return {"error": str(e)}

    def terminate_job(self, job_id: int) -> Dict[str, Any]:
        r"""Terminate a running job.

        Args:
            job_id (int): The ID of the job to terminate.

        Returns:
            Dict[str, Any]: The result of the termination request.
        """
        try:
            self._job.terminate(job_id)  # type: ignore[union-attr]
            return {"status": "Job terminated successfully"}
        except Exception as e:
            logger.error(f"Error terminating job: {e}")
            return {"error": str(e)}

    def kill_job(self, job_id: int) -> Dict[str, Any]:
        r"""Kill a running job.

        Args:
            job_id (int): The ID of the job to kill.

        Returns:
            Dict[str, Any]: The result of the kill request.
        """
        try:
            self._job.kill(job_id)  # type: ignore[union-attr]
            return {"status": "Job killed successfully"}
        except Exception as e:
            logger.error(f"Error killing job: {e}")
            return {"error": str(e)}

    def get_job_logs(
        self,
        job_id: int,
        log_file: str = "STDOUTERR",
        page: int = -1,
        page_size: int = 8192,
    ) -> str:
        r"""Get logs for a specific job.

        Args:
            job_id (int): The ID of the job.
            log_file (str, optional): The log file to get.
                (default: :obj:`STDOUTERR`)
            page (int, optional): The page number.
                (default: :obj:`-1`)
            page_size (int, optional): The page size.
                (default: :obj:`8192`)

        Returns:
            str: The log contents.
        """
        try:
            return self._job.log(  # type: ignore[union-attr]
                job_id, log_file=log_file, page=page, page_size=page_size
            )
        except Exception as e:
            logger.error(f"Error getting job logs: {e}")
            return f"Error retrieving logs: {e!s}"

    def create_job_group(
        self, project_id: int, job_group_name: str
    ) -> Dict[str, Any]:
        r"""Create a job group.

        Args:
            project_id (int): The ID of the project.
            job_group_name (str): The name of the job group.

        Returns:
            Dict[str, Any]: The result of the job group creation.
        """
        try:
            self._job.create_job_group(project_id, job_group_name)  # type: ignore[union-attr]
            return {"status": "Job group created successfully"}
        except Exception as e:
            logger.error(f"Error creating job group: {e}")
            return {"error": str(e)}

    def download_job_results(
        self, job_id: int, save_path: str
    ) -> Dict[str, Any]:
        r"""Download the results of a job.

        Args:
            job_id (int): The ID of the job.
            save_path (str): The path to save the results to.

        Returns:
            Dict[str, Any]: The result of the download request.
        """
        try:
            self._job.download(job_id, save_path)  # type: ignore[union-attr]
            return {
                "status": "Job results downloaded successfully",
                "path": save_path,
            }
        except Exception as e:
            logger.error(f"Error downloading job results: {e}")
            return {"error": str(e)}

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [
            FunctionTool(self.submit_job),
            FunctionTool(self.get_job_details),
            FunctionTool(self.terminate_job),
            FunctionTool(self.kill_job),
            FunctionTool(self.get_job_logs),
            FunctionTool(self.create_job_group),
            FunctionTool(self.download_job_results),
        ]
