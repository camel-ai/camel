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

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine
from camel.storages.database_storages.database_manager import DatabaseManager
from camel.messages.base import BaseMessage
from camel.interpreters.interpreter_error import InterpreterError
import json
import logging

logger = logging.getLogger(__name__)

INSERT_MESSAGE = '''
INSERT INTO message
(role_name, role_type, meta_dict, content, agent_id, message_id, 
video_path,image_path)
VALUES 
(:role_name, :role_type, :meta_dict, :content, :agent_id, 
:message_id, :video_path, :image_path);
'''

CREATE_MESSAGE_TABLE = '''
CREATE TABLE message (
	id serial4 NOT NULL,
	role_name varchar(255) NOT NULL,
	role_type varchar(255) NOT NULL,
	meta_dict jsonb NULL,
	"content" text NOT NULL,
	agent_id varchar(255) NULL,
	message_id varchar(255) NULL,
	video_path varchar(255) NULL,
	image_path varchar(255) NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT message_pkey PRIMARY KEY (id)
);
'''

CREATE_AGENT_TABLE = '''
CREATE TABLE agent (
	id serial4 NOT NULL,
	agent_id varchar(255) NULL,
	model_type varchar(255) NOT NULL,
	model_config_dict jsonb NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT agent_pkey PRIMARY KEY (id)
);
'''

class PostgreSQLManager(DatabaseManager):
    r"""A class for the manages interactions with a PostgreSQL database.

    Args:
        conn_str (str): The connection string used to connect to the PostgreSQL database.
    """
    def __init__(self, conn_str: str):
        self.engine: Engine = create_engine(conn_str)
        self.__tabels_exit()
    
    def save_agent_infos(self):
        pass

    def __tabels_exit(self):
        inspector = inspect(self.engine)
        if not inspector.has_table("message"):
            raise InterpreterError(f"please use {CREATE_MESSAGE_TABLE} to"
                                   "create message table.")
        elif not inspector.has_table("agent"):
            raise InterpreterError(f"please use {CREATE_AGENT_TABLE} to"
                                   "create agent table.")

    def save_message_infos(self, base_message:BaseMessage):
        try:
            # Convert meta_dict to a JSON string
            meta_dict_json = json.dumps(base_message.meta_dict) \
            if base_message.meta_dict else None

            # Prepare the SQL insert statement or use ORM
            insert_stmt = text(INSERT_MESSAGE)
            # Prepare the parameters for the SQL statement
            params = [{
                'role_name': base_message.role_name,
                'role_type': str(base_message.role_type.value),
                'meta_dict': meta_dict_json,
                'content': base_message.content,
                'agent_id': '',
                'message_id': '',
                'video_path': '',
                'image_path': '',
            }]
            # Conditionally add agent_id if it exists
            if hasattr(base_message, 'agent_id'):
                params[0]['agent_id'] = base_message.agent_id

            # Conditionally add message_id if it exists
            if hasattr(base_message, 'message_id'):
                params[0]['message_id'] = base_message.message_id

            with self.engine.begin() as conn:
                conn.execute(insert_stmt, params)
        except Exception as e:
            logger.error(f"Error loading records: {e}")