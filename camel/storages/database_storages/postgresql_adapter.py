# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from camel.storages.database_storages import DatabaseInterface

# PostgreSQL adapter
class PostgreSQLAdapter(DatabaseInterface):
    
    def __init__(self, conn_str: str):
        self.engine: Engine = create_engine(conn_str)

    def save_agent_message(self):
        try:
            pass
        except:
            pass