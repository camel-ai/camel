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
from typing import Dict, Any, List
from camel.interpreters import (
    BaseInterpreter,
)
from abc import ABC, abstractmethod
import psycopg2
import sqlite3

from camel.agents.tool_agents.base import BaseToolAgent
from camel.interpreters.interpreter_error import InterpreterError



class DatabaseConnector(ABC):
    r"""Abstract base class for database connectors."""

    @abstractmethod
    def run_query(self, query: str) -> str:
        r"""Execute a SQL query and return results as a string."""
        pass
class SQLiteConnector(DatabaseConnector):
    r"""SQLite connector for executing SQL queries.

    Args:
        db_path (str): Path to the SQLite database file.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path

    def run_query(self, query: str) -> str:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description] if cursor.description else []

            conn.commit()
            conn.close()

            if not rows:
                return "Query executed successfully. No rows returned."

            # Format as text table
            result = "\t".join(column_names) + "\n"
            result += "\n".join(["\t".join(map(str, row)) for row in rows])
            return result
        except Exception as e:
            return f"SQLite query failed: {e}"


class PostgresConnector(DatabaseConnector):
    r"""PostgreSQL connector for executing SQL queries.

    Args:
        host (str): PostgreSQL host address.
        port (int): PostgreSQL port (default: 5432).
        user (str): Username for authentication.
        password (str): Password for authentication.
        database (str): Name of the database to connect to.
    """

    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        self.conn_info = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "dbname": database,
        }

    def run_query(self, query: str) -> str:
        try:
            conn = psycopg2.connect(**self.conn_info)
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description] if cursor.description else []

            conn.commit()
            conn.close()

            if not rows:
                return "Query executed successfully. No rows returned."

            result = "\t".join(column_names) + "\n"
            result += "\n".join(["\t".join(map(str, row)) for row in rows])
            return result
        except Exception as e:
            return f"PostgreSQL query failed: {e}"

class SQLQueryInterpreter(BaseInterpreter):
    r"""Interpreter that executes SQL code blocks on a given database connector.

    Args:
        connector (DatabaseConnector): An object capable of executing SQL queries.

    Supported code_type: "sql"
    """

    def __init__(self, connector: DatabaseConnector):
        self.connector = connector

    def run(self, code: str, code_type: str) -> str:
        if code_type.lower() != "sql":
            raise InterpreterError(f"Unsupported code type: {code_type}")
        try:
            return self.connector.run_query(code)
        except Exception as e:
            raise InterpreterError(f"SQL execution error: {e}")

    def supported_code_types(self) -> List[str]:
        return ["sql"]

    def update_action_space(self, action_space: Dict[str, BaseToolAgent]) -> None:
        pass  # No-op


def DatabaseInterpreter(db_config: Dict[str, Any]) -> BaseInterpreter:
    r"""Creates a database interpreter based on the provided configuration.

    Args:
        db_config (Dict[str, Any]): Configuration dictionary for database.
            For SQLite: {"type": "sqlite", "path": "./db.sqlite"}
            For Postgres: {
                "type": "postgres",
                "host": ..., "port": ..., "user": ..., "password": ..., "database": ...
            }

    Returns:
        BaseInterpreter: A code interpreter capable of executing SQL queries.
    """
    db_type = db_config.get("type")
    if db_type == "sqlite":
        path = db_config.get("path")
        if not path:
            raise ValueError("Missing 'path' for SQLite config.")
        connector = SQLiteConnector(path)
    elif db_type == "postgres":
        connector = PostgresConnector(
            host=db_config["host"],
            port=db_config.get("port", 5432),
            user=db_config["user"],
            password=db_config["password"],
            database=db_config["database"],
        )
    else:
        raise ValueError(f"Unsupported database type: {db_type}")
    return SQLQueryInterpreter(connector)