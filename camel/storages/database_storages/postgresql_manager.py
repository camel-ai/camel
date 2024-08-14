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

import json
import logging
from typing import Dict, List

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

from camel.interpreters.interpreter_error import InterpreterError
from camel.messages import OpenAIMessage
from camel.messages.base import BaseMessage
from camel.storages.database_storages.database_manager import DatabaseManager
from camel.types.enums import OpenAIBackendRole

logger = logging.getLogger(__name__)

# SQL insert statement for adding a new message record to the `message` table
INSERT_MESSAGE = '''
INSERT INTO message
(role_name, role_type, meta_dict, content, agent_id, message_id, 
video_path, image_path, is_system_message)
VALUES 
(:role_name, :role_type, :meta_dict, :content, :agent_id, 
:message_id, :video_path, :image_path, :is_system_message);
'''

# SQL insert statement for adding a new agent record to the `agent` table
INSERT_AGENT = '''
INSERT INTO agent
(model_type, model_config_dict, agent_id)
VALUES(:model_type_value, :model_config_dict, :agent_id);
'''

# SQL statement to create the `message` table with the specified columns and 
# constraints
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
	is_system_message bool DEFAULT false NULL,
	CONSTRAINT message_pkey PRIMARY KEY (id)
);
'''

# SQL statement to create the `agent` table with the specified columns and 
# constraints
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
    r"""A class for the manages interactions with a PostgreSQL database."""

    def __init__(self, conn_str: str):
        '''
        Args:
            conn_str (str): The connection string used to connect to the
            PostgreSQL database, the format follow this: postgresql://
            user:password@localhost/dbname
        '''
        self.engine: Engine = create_engine(conn_str)
        # Check if required tables exist in the database
        self.__tabels_exit()
    
    def save_memory_infos(self, openai_messages: List[OpenAIMessage], 
                                  role_type: str, role_name: str) -> None:
        '''
        Saves memory information related to OpenAI messages into the database.

        Args:
            openai_messages (List[OpenAIMessage]): A list of OpenAI messages 
            to be saved.
            role_type (str): The type of role associated with the messages.
            role_name (str): The name of the role associated with the messages.
        '''
        try:
            if openai_messages and len(openai_messages) > 0:
                for openai_message in openai_messages:
                    with self.engine.begin() as conn:
                        is_system_message = False
                        if openai_message['role'] == \
                        OpenAIBackendRole.SYSTEM.value:
                            is_system_message = True

                        params = [{
                        'role_name': role_name,
                        'role_type': role_type,
                        'meta_dict': None,
                        'content': openai_message['content'],
                        'agent_id': '',
                        'message_id': '',
                        'video_path': '',
                        'image_path': '',
                        'is_system_message': is_system_message}]

                        # Prepare the SQL insert statement of message table
                        insert_stmt = text(INSERT_MESSAGE)
                        conn.execute(insert_stmt, params)
                    
        except Exception as e:
            logger.error(f"Error loading records: {e}")

    def save_agent_infos(self, model_config_dict: Dict, 
                         model_type_value: str) -> None:
        '''
        Saves agent information to the database.

        Args:
            model_config_dict (Dict): A dictionary containing the agent's 
            configuration settings.
            model_type_value (str): The type of model associated with the agent.
        '''
        try:
            # Convert the dictionary values to strings to ensure compatibility 
            # with the database
            model_config_str_dict = {}
            for key, value in model_config_dict.items(): 
                model_config_str_dict[key] = str(value)   
            
            # Convert the Python dictionary to a JSON string
            model_config_json = json.dumps(model_config_str_dict)

            # Prepare the SQL insert statement of message table
            insert_stmt = text(INSERT_AGENT)

            # Prepare the parameters for the SQL statement
            params = [{
                "model_config_dict": model_config_json,
                "model_type_value": model_type_value,
                "agent_id": ""
            }]

            with self.engine.begin() as conn:
                conn.execute(insert_stmt, params)
        except Exception as e:
            logger.error(f"Error loading records: {e}")

    def __tabels_exit(self) -> None:
        '''
        Checks if the necessary tables ("message" and "agent") exist in the
        database. If not, raises an InterpreterError suggesting the creation
        of the missing tables.
        '''
        inspector = inspect(self.engine)
        if not inspector.has_table("message"):
            raise InterpreterError(
                f"please use {CREATE_MESSAGE_TABLE} to" "create message table."
            )
        elif not inspector.has_table("agent"):
            raise InterpreterError(
                f"please use {CREATE_AGENT_TABLE} to" "create agent table."
            )

    def save_message_infos(
        self, base_message: BaseMessage, is_system_message: bool
    ) -> None:
        '''
        Saves message information to the database.

        Args:
            base_message (BaseMessage): The system message of chat agent.
            is_system_message (bool): Indicates if the message is a system
            message.
        '''
        try:
            # Convert meta_dict to a JSON string
            meta_dict_json = (
                json.dumps(base_message.meta_dict)
                if base_message.meta_dict
                else None
            )

            # Prepare the SQL insert statement of message table
            insert_stmt = text(INSERT_MESSAGE)
            # Prepare the parameters for the SQL statement
            params = [
                {
                    'role_name': base_message.role_name,
                    'role_type': str(base_message.role_type.value),
                    'meta_dict': meta_dict_json,
                    'content': base_message.content,
                    'agent_id': '',
                    'message_id': '',
                    'video_path': '',
                    'image_path': '',
                    'is_system_message': is_system_message,
                }
            ]
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
