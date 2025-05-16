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
from typing import TYPE_CHECKING, Any, List, Optional, Union

if TYPE_CHECKING:
    from apify_client.clients import DatasetClient

from camel.utils import api_keys_required

from .base_loader import BaseLoader


class Apify:
    r"""Apify is a platform that allows you to automate any web workflow.

    Args:
        api_key (Optional[str]): API key for authenticating with the Apify API.
    """

    @api_keys_required(
        [
            ("api_key", "APIFY_API_KEY"),
        ]
    )
    def __init__(
        self,
        api_key: Optional[str] = None,
    ) -> None:
        from apify_client import ApifyClient

        self._api_key = api_key or os.environ.get("APIFY_API_KEY")
        self.client = ApifyClient(token=self._api_key)

    def run_actor(
        self,
        actor_id: str,
        run_input: Optional[dict] = None,
        content_type: Optional[str] = None,
        build: Optional[str] = None,
        max_items: Optional[int] = None,
        memory_mbytes: Optional[int] = None,
        timeout_secs: Optional[int] = None,
        webhooks: Optional[list] = None,
        wait_secs: Optional[int] = None,
    ) -> Optional[dict]:
        r"""Run an actor on the Apify platform.

        Args:
            actor_id (str): The ID of the actor to run.
            run_input (Optional[dict]): The input data for the actor. Defaults
                to `None`.
            content_type (str, optional): The content type of the input.
            build (str, optional): Specifies the Actor build to run. It can be
                either a build tag or build number. By default, the run uses
                the build specified in the default run configuration for the
                Actor (typically latest).
            max_items (int, optional): Maximum number of results that will be
                returned by this run. If the Actor is charged per result, you
                will not be charged for more results than the given limit.
            memory_mbytes (int, optional): Memory limit for the run, in
                megabytes. By default, the run uses a memory limit specified in
                the default run configuration for the Actor.
            timeout_secs (int, optional): Optional timeout for the run, in
                seconds. By default, the run uses timeout specified in the
                default run configuration for the Actor.
            webhooks (list, optional): Optional webhooks
                (https://docs.apify.com/webhooks) associated with the Actor
                run, which can be used to receive a notification, e.g. when the
                Actor finished or failed. If you already have a webhook set up
                for the Actor, you do not have to add it again here.
            wait_secs (int, optional): The maximum number of seconds the server
                waits for finish. If not provided, waits indefinitely.

        Returns:
            Optional[dict]: The output data from the actor if successful.
            # please use the 'defaultDatasetId' to get the dataset

        Raises:
            RuntimeError: If the actor fails to run.
        """
        try:
            return self.client.actor(actor_id).call(
                run_input=run_input,
                content_type=content_type,
                build=build,
                max_items=max_items,
                memory_mbytes=memory_mbytes,
                timeout_secs=timeout_secs,
                webhooks=webhooks,
                wait_secs=wait_secs,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to run actor {actor_id}: {e}") from e

    def get_dataset_client(
        self,
        dataset_id: str,
    ) -> "DatasetClient":
        r"""Get a dataset client from the Apify platform.

        Args:
            dataset_id (str): The ID of the dataset to get the client for.

        Returns:
            DatasetClient: The dataset client.

        Raises:
            RuntimeError: If the dataset client fails to be retrieved.
        """
        try:
            return self.client.dataset(dataset_id)
        except Exception as e:
            raise RuntimeError(
                f"Failed to get dataset {dataset_id}: {e}"
            ) from e

    def get_dataset(
        self,
        dataset_id: str,
    ) -> Optional[dict]:
        r"""Get a dataset from the Apify platform.

        Args:
            dataset_id (str): The ID of the dataset to get.

        Returns:
            dict: The dataset.

        Raises:
            RuntimeError: If the dataset fails to be retrieved.
        """
        try:
            return self.get_dataset_client(dataset_id).get()
        except Exception as e:
            raise RuntimeError(
                f"Failed to get dataset {dataset_id}: {e}"
            ) from e

    def update_dataset(
        self,
        dataset_id: str,
        name: str,
    ) -> dict:
        r"""Update a dataset on the Apify platform.

        Args:
            dataset_id (str): The ID of the dataset to update.
            name (str): The new name for the dataset.

        Returns:
            dict: The updated dataset.

        Raises:
            RuntimeError: If the dataset fails to be updated.
        """
        try:
            return self.get_dataset_client(dataset_id).update(name=name)
        except Exception as e:
            raise RuntimeError(
                f"Failed to update dataset {dataset_id}: {e}"
            ) from e

    def get_dataset_items(
        self,
        dataset_id: str,
    ) -> List:
        r"""Get items from a dataset on the Apify platform.

        Args:
            dataset_id (str): The ID of the dataset to get items from.

        Returns:
            list: The items in the dataset.

        Raises:
            RuntimeError: If the items fail to be retrieved.
        """
        try:
            items = self.get_dataset_client(dataset_id).list_items().items
            return items
        except Exception as e:
            raise RuntimeError(
                f"Failed to get dataset items {dataset_id}: {e}"
            ) from e

    def get_datasets(
        self,
        unnamed: Optional[bool] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        desc: Optional[bool] = None,
    ) -> List[dict]:
        r"""Get all named datasets from the Apify platform.

        Args:
            unnamed (bool, optional): Whether to include unnamed key-value
                stores in the list
            limit (int, optional): How many key-value stores to retrieve
            offset (int, optional): What key-value store to include as first
                when retrieving the list
            desc (bool, optional): Whether to sort the key-value stores in
                descending order based on their modification date

        Returns:
            List[dict]: The datasets.

        Raises:
            RuntimeError: If the datasets fail to be retrieved.
        """
        try:
            return (
                self.client.datasets()
                .list(unnamed=unnamed, limit=limit, offset=offset, desc=desc)
                .items
            )
        except Exception as e:
            raise RuntimeError(f"Failed to get datasets: {e}") from e


class ApifyLoader(BaseLoader):
    def __init__(self, config) -> None:
        super().__init__(config)
        # Initialize the underlying Apify class.
        self._api_key = config.get("api_key") or os.environ.get(
            "APIFY_API_KEY"
        )
        self.apify = Apify(api_key=self._api_key)

    def load(self, source: str, **kwargs: Any) -> Union[dict, List[dict]]:
        functionality = kwargs.get("functionality", "run_actor")

        if functionality == "run_actor":
            result = self.apify.run_actor(
                actor_id=source,
                run_input=kwargs.get("run_input"),
                content_type=kwargs.get("content_type"),
                build=kwargs.get("build"),
                max_items=kwargs.get("max_items"),
                memory_mbytes=kwargs.get("memory_mbytes"),
                timeout_secs=kwargs.get("timeout_secs"),
                webhooks=kwargs.get("webhooks"),
                wait_secs=kwargs.get("wait_secs"),
            )
            return result if result else {}

        elif functionality == "get_dataset":
            dataset_id = source
            if not dataset_id:
                raise ValueError(
                    "dataset_id is required for get_dataset functionality."
                )
            result = self.apify.get_dataset(dataset_id)
            return result if result else {}

        elif functionality == "update_dataset":
            dataset_id = source
            name = kwargs.get("name")
            if not dataset_id or not name:
                raise ValueError("Both dataset_id and name are required.")
            return self.apify.update_dataset(dataset_id, name)

        elif functionality == "get_dataset_items":
            dataset_id = source
            if not dataset_id:
                raise ValueError(
                    "dataset_id is required for get_dataset_items."
                )
            return self.apify.get_dataset_items(dataset_id)
        elif functionality == "get_datasets":
            return self.apify.get_datasets(
                unnamed=kwargs.get("unnamed"),
                limit=kwargs.get("limit"),
                offset=kwargs.get("offset"),
                desc=kwargs.get("desc"),
            )
        else:
            raise ValueError(f"Unsupported functionality: {functionality}")

    @property
    def supported_formats(self) -> set:
        return {"apify"}
