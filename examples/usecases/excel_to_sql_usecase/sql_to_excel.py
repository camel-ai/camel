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
from camel.messages import BaseMessage
from camel.agents import EmbodiedAgent
from camel.types import (
    RoleType,
)
from camel.interpreters.interpreter_error import InterpreterError

from typing import List, Dict
from camel.agents.tool_agents.base import BaseToolAgent
import argparse
import sqlite3
import openpyxl
import json
from camel.interpreters.base import BaseInterpreter
import logging
import sys
import pandas as pd

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.propagate = False

if not logger.handlers:
    file_handler = logging.FileHandler("../process_history.log",
                                       encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


from dotenv import load_dotenv
import os

load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")



class ExcelPythonInterpreter(BaseInterpreter):
    def run(self, code: str, code_type: str) -> str:
        if code_type.lower() != "python":
            raise InterpreterError("Only Python code is supported")

        try:
            exec(code, {})
            return "Python executed."
        except Exception as e:
            return f"Execution failed: {e}"

    def supported_code_types(self) -> List[str]:
        return ["python"]

    def update_action_space(self,
                            action_space: Dict[str, BaseToolAgent]) -> None:
        pass


def init_sqlite_example(db_path: str):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Delete old table
    cur.execute("DROP TABLE IF EXISTS employees")

    # Create new table
    cur.execute("""
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            name TEXT,
            age INTEGER,
            salary REAL,
            gender TEXT,
            hire_date TEXT
        )
    """)

    # Insert sample employee data
    employees = [
        ("Alice", 30, 70000.0, "Female", "2020-05-01"),
        ("Bob", 40, 85000.0, "Male", "2018-03-15"),
        ("Charlie", 28, 62000.0, "Male", "2021-07-22"),
        ("Diana", 35, 91000.0, "Female", "2017-11-03"),
        ("Eve", 26, 56000.0, "Female", "2022-09-10"),
    ]

    cur.executemany("""
        INSERT INTO employees (name, age, salary, gender, hire_date)
        VALUES (?, ?, ?, ?, ?)
    """, employees)

    conn.commit()
    conn.close()


def run_workflow(template_path: str, output_path: str, database_schema: str):
    excel_interpreter = ExcelPythonInterpreter()

    # Step 1: Python Agent extracts fields
    agent1 = EmbodiedAgent(
        system_message=BaseMessage("python_agent", RoleType.ASSISTANT, {},
                                   f"You are a Python engineer who helps "
                                   f"users work with Excel files. Write "
                                   f"Python code to extract Excel "
                                   f"information. Do not include pip "
                                   f"install. Excel file path: "
                                   f"{template_path}"),
        code_interpreter=excel_interpreter
    )

    extract_msg = BaseMessage("user", RoleType.USER, {},
                              "Please extract the field names from the first "
                              "row of the Excel template.")
    response1 = agent1.step(extract_msg)
    print(response1.msgs[0].content)

    # Step 2: SQL Agent generates a query
    agent2 = EmbodiedAgent(
        system_message=BaseMessage("sql_agent", RoleType.ASSISTANT, {},
                                   f"You are a SQL engineer helping users "
                                   f"generate SQL queries based on the "
                                   f"fields. Generate SQL code and mark it "
                                   f"as type 'sql'. Table schema: "
                                   f"{database_schema}"),
        database={
            "type": "sqlite",
            "path": "example.db"
        },
    )

    query_msg = BaseMessage("user", RoleType.USER, {},
                            f"Please generate an SQL query based on the "
                            f"following fields: {response1.msgs[0].content}")
    response2 = agent2.step(query_msg)
    print(response2.msgs[0].content)

    # Step 3: Python Agent writes to Excel
    final_msg = BaseMessage("user", RoleType.USER, {},
                            f"Please use write_data_to_excel(json_data) to "
                            f"write the following data to Excel:\n"
                            f"{response2.msgs[0].content}, output file: "
                            f"{output_path}")
    response3 = agent1.step(final_msg)
    print(response3.msgs[0].content)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run workflow with optional example mode.")

    parser.add_argument("--example", action="store_true",
                        help="Run in example mode with default values.")
    parser.add_argument("--template_path", type=str,
                        help="Path to the Excel template.")
    parser.add_argument("--output_path", type=str,
                        help="Path to save the output Excel file.")
    parser.add_argument("--database_schema", type=str,
                        help="Database schema in plain text format.")

    args = parser.parse_args()

    if args.example:
        template_path = "../template.xlsx"
        output_path = "../output.xlsx"
        database_schema = """
        TABLE employees
            id INTEGER PRIMARY KEY,
            name TEXT,
            age INTEGER,
            salary REAL,
            gender TEXT,
            hire_date TEXT
        """
        init_sqlite_example('example.db')
    else:
        # Ensure all required arguments are provided
        if (not args.template_path or not args.output_path or not
        args.database_schema):
            parser.error(
                "--template_path, --output_path, and --database_schema are "
                "required when not in --example mode.")
        template_path = args.template_path
        output_path = args.output_path
        database_schema = args.database_schema

    run_workflow(template_path, output_path, database_schema)
