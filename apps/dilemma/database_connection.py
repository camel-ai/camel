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
import sqlalchemy
from google.cloud.sql.connector import Connector, IPTypes

from camel.logger import get_logger

# import os
# os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = \
#     "/path/to/camel-lm-XXXXXXXXX.json"

logger = get_logger(__name__)


class DatabaseConnection:
    def __init__(self):
        INSTANCE_CONNECTION_NAME = "camel-lm:me-central1:camel-dilemma"
        logger.info(f"Instance connection name is: {INSTANCE_CONNECTION_NAME}")
        DB_USER = "dkuser"
        DB_PASS = "camel230509"
        DB_NAME = "dilemma_choices"

        self.connector = Connector()

        def getconn():
            conn = self.connector.connect(
                INSTANCE_CONNECTION_NAME,
                "pymysql",
                user=DB_USER,
                password=DB_PASS,
                db=DB_NAME,
                ip_type=IPTypes.PRIVATE,
            )
            return conn

        self.pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=getconn,
        )

    def __del__(self):
        self.connector.close()

    def add_record(self, file_name: str, who_is_better: str):
        with self.pool.connect() as db_conn:
            insert_stmt = sqlalchemy.text(
                "INSERT INTO choices2 (file_name, who_is_better, date)"
                " VALUES (:file_name, :who_is_better, NOW())"
            )
            db_conn.execute(
                insert_stmt,
                parameters={
                    "file_name": file_name,
                    "who_is_better": who_is_better,
                },
            )
            db_conn.commit()
