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

import logging
from typing import Any, Dict, List

from camel.storages import RedisStorage


def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    sid = "example_sid"
    url = "redis://localhost:6379"
    storage = RedisStorage(sid=sid, url=url)

    with storage:
        records: List[Dict[str, Any]] = [
            {"id": 1, "name": "Record1"},
            {"id": 2, "name": "Record2"},
        ]

        storage.save(records)
        logger.info("Records saved successfully.")

        loaded_records = storage.load()
        logger.info(f"Loaded records: {loaded_records}")
        """
        Loaded records: [{'id': 1, 'name': 'Record1'}, {'id': 2, 'name': 
        'Record2'}]
        """

        storage.clear()
        logger.info("Records cleared successfully.")
        """
        Records cleared successfully.
        """

        loaded_records_after_clear = storage.load()
        logger.info(
            f"Loaded records after clear: {loaded_records_after_clear}"
        )
        """
        Loaded records after clear: []
        """


if __name__ == "__main__":
    main()
