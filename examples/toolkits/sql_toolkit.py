# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
import os
import tempfile

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.toolkits.sql_toolkit import SQLToolkit
from camel.types import ModelPlatformType, ModelType

# Example 1: Initialize SQL Toolkit with in-memory database
sql_toolkit = SQLToolkit(database_path=":memory:", read_only=False)

# Create a table
sql_toolkit.execute_query(
    "CREATE TABLE users (id INTEGER, name TEXT, age INTEGER, email TEXT)"
)

# Insert data
sql_toolkit.execute_query(
    "INSERT INTO users VALUES (1, 'Alice', 25, 'alice@example.com')"
)
sql_toolkit.execute_query(
    "INSERT INTO users VALUES (2, 'Bob', 30, 'bob@example.com')"
)
sql_toolkit.execute_query(
    "INSERT INTO users VALUES (3, 'Charlie', 28, 'charlie@example.com')"
)

# Query data
result = sql_toolkit.execute_query("SELECT * FROM users")
print("All users:")
print(result)

'''
===============================================================================
All users:
[{'id': 1, 'name': 'Alice', 'age': 25, 'email': 'alice@example.com'},
 {'id': 2, 'name': 'Bob', 'age': 30, 'email': 'bob@example.com'},
 {'id': 3, 'name': 'Charlie', 'age': 28, 'email': 'charlie@example.com'}]
===============================================================================
'''

# Example 2: SELECT with WHERE clause
result = sql_toolkit.execute_query(
    "SELECT name, age FROM users WHERE age > 26"
)
print("\nUsers older than 26:")
print(result)

'''
===============================================================================
Users older than 26:
[{'name': 'Bob', 'age': 30}, {'name': 'Charlie', 'age': 28}]
===============================================================================
'''

# Example 3: JOIN query
# Create orders table
sql_toolkit.execute_query(
    "CREATE TABLE orders "
    "(id INTEGER, user_id INTEGER, product TEXT, amount REAL)"
)
sql_toolkit.execute_query("INSERT INTO orders VALUES (1, 1, 'Laptop', 999.99)")
sql_toolkit.execute_query("INSERT INTO orders VALUES (2, 1, 'Mouse', 29.99)")
sql_toolkit.execute_query(
    "INSERT INTO orders VALUES (3, 2, 'Keyboard', 79.99)"
)

# JOIN query
result = sql_toolkit.execute_query(
    """
    SELECT u.name, o.product, o.amount
    FROM users u
    JOIN orders o ON u.id = o.user_id
    ORDER BY o.amount DESC
    """
)
print("\nUser orders:")
print(result)

'''
===============================================================================
User orders:
[{'name': 'Alice', 'product': 'Laptop', 'amount': 999.99},
 {'name': 'Bob', 'product': 'Keyboard', 'amount': 79.99},
 {'name': 'Alice', 'product': 'Mouse', 'amount': 29.99}]
===============================================================================
'''

# Example 4: Common Table Expression (CTE)
result = sql_toolkit.execute_query(
    """
    WITH user_totals AS (
        SELECT u.name, SUM(o.amount) as total_spent
        FROM users u
        JOIN orders o ON u.id = o.user_id
        GROUP BY u.name
    )
    SELECT * FROM user_totals
    ORDER BY total_spent DESC
    """
)
print("\nTotal spending per user:")
print(result)

'''
===============================================================================
Total spending per user:
[{'name': 'Alice', 'total_spent': 1029.98},
 {'name': 'Bob', 'total_spent': 79.99}]
===============================================================================
'''

# Example 5: UPDATE and DELETE operations
sql_toolkit.execute_query("UPDATE users SET age = 26 WHERE name = 'Alice'")
result = sql_toolkit.execute_query(
    "SELECT name, age FROM users WHERE name = 'Alice'"
)
print("\nUpdated Alice's age:")
print(result)

sql_toolkit.execute_query("DELETE FROM users WHERE age < 27")
result = sql_toolkit.execute_query("SELECT * FROM users")
print("\nUsers after deletion:")
print(result)

'''
===============================================================================
Updated Alice's age:
[{'name': 'Alice', 'age': 26}]

Users after deletion:
[{'id': 2, 'name': 'Bob', 'age': 30, 'email': 'bob@example.com'},
 {'id': 3, 'name': 'Charlie', 'age': 28, 'email': 'charlie@example.com'}]
===============================================================================
'''

# Example 6: Read-only mode
# Create a new toolkit in read-only mode
readonly_toolkit = SQLToolkit(database_path=":memory:", read_only=True)

# First, set up some data (need to do this before enabling read-only)
# Actually, we need to create data first, then switch to read-only
readonly_toolkit.read_only = False
readonly_toolkit.execute_query(
    "CREATE TABLE products (id INTEGER, name TEXT, price REAL)"
)
readonly_toolkit.execute_query(
    "INSERT INTO products VALUES (1, 'Widget', 19.99)"
)
readonly_toolkit.read_only = True

# SELECT works in read-only mode
result = readonly_toolkit.execute_query("SELECT * FROM products")
print("\nProducts (read-only mode):")
print(result)

# INSERT would fail in read-only mode
try:
    readonly_toolkit.execute_query(
        "INSERT INTO products VALUES (2, 'Gadget', 29.99)"
    )
except ValueError as e:
    print(f"\nRead-only mode correctly blocked INSERT: {e}")

'''
===============================================================================
Products (read-only mode):
[{'id': 1, 'name': 'Widget', 'price': 19.99}]

Read-only mode correctly blocked INSERT: Write operations are not allowed in
read-only mode. The query contains write operations (INSERT, UPDATE, DELETE,
DROP, CREATE, ALTER, TRUNCATE, etc.). Only SELECT queries are permitted.
===============================================================================
'''

# Example 7: EXPLAIN query
result = sql_toolkit.execute_query(
    "EXPLAIN SELECT * FROM users WHERE age > 25"
)
print("\nQuery execution plan:")
print(result)

'''
===============================================================================
Query execution plan:
[{'explain_key': 'logical_plan', 'explain_value': '...'},
 {'explain_key': 'physical_plan', 'explain_value': '...'}]
===============================================================================
'''

# Example 8: File-based database (persistent storage)
# Create a temporary file for the database
with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
    db_path = tmp_file.name

# Remove the empty file so DuckDB can create a new database
try:
    os.unlink(db_path)
except Exception:
    pass

# Create toolkit with file-based database
file_toolkit = SQLToolkit(database_path=db_path, read_only=False)

# Create table and insert data
file_toolkit.execute_query(
    "CREATE TABLE inventory (id INTEGER, item TEXT, quantity INTEGER)"
)
file_toolkit.execute_query("INSERT INTO inventory VALUES (1, 'Apples', 100)")
file_toolkit.execute_query("INSERT INTO inventory VALUES (2, 'Bananas', 150)")

# Close connection
file_toolkit._connection.close()

# Reopen connection to same file - data persists!
file_toolkit2 = SQLToolkit(database_path=db_path, read_only=False)
result = file_toolkit2.execute_query("SELECT * FROM inventory")
print("\nPersistent inventory data:")
print(result)

# Cleanup
file_toolkit2._connection.close()
try:
    os.unlink(db_path)
except Exception:
    pass

'''
===============================================================================
Persistent inventory data:
[{'id': 1, 'item': 'Apples', 'quantity': 100},
 {'id': 2, 'item': 'Bananas', 'quantity': 150}]
===============================================================================
'''

# Example 9: Using SQLite Database
print("\n" + "=" * 80)
print("Example 9: Using SQLite Database")
print("=" * 80)

# SQLite is built into Python and works similarly to DuckDB
# Just specify database_type="sqlite" to use SQLite instead of DuckDB
sqlite_toolkit = SQLToolkit(
    database_path=":memory:", database_type="sqlite", read_only=False
)

# Create a table
sqlite_toolkit.execute_query(
    "CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, price REAL)"
)

# Insert data
sqlite_toolkit.execute_query(
    "INSERT INTO products (name, price) VALUES ('Laptop', 999.99)"
)
sqlite_toolkit.execute_query(
    "INSERT INTO products (name, price) VALUES ('Mouse', 29.99)"
)

# Query data
result = sqlite_toolkit.execute_query("SELECT * FROM products")
print("\nSQLite products:")
print(result)

# List tables
tables = sqlite_toolkit.list_tables()
print(f"\nSQLite tables: {tables}")

# Get table info
table_info = sqlite_toolkit.get_table_info("products")
print("\nSQLite table info:")
print(f"  Columns: {len(table_info['columns'])}")
print(f"  Primary keys: {table_info['primary_keys']}")
print(f"  Row count: {table_info['row_count']}")

'''
===============================================================================
SQLite products:
[{'id': 1, 'name': 'Laptop', 'price': 999.99},
 {'id': 2, 'name': 'Mouse', 'price': 29.99}]

SQLite tables: ['products']

SQLite table info:
  Columns: 3
  Primary keys: ['id']
  Row count: 2
===============================================================================
'''

# Example 10: Schema Discovery - Using built-in toolkit methods
print("\n" + "=" * 80)
print("Example 10: Schema Discovery (Using Toolkit Methods)")
print("=" * 80)
# Note: This example uses DuckDB (default), but SQLite works the same way

# Create a new database with multiple tables including primary and foreign keys
schema_toolkit = SQLToolkit(database_path=":memory:", read_only=False)

# Set up sample database with relationships
schema_toolkit.execute_query(
    "CREATE TABLE departments (id INTEGER PRIMARY KEY, name TEXT, budget REAL)"
)
schema_toolkit.execute_query(
    """
    CREATE TABLE employees (
        id INTEGER PRIMARY KEY,
        name TEXT,
        department_id INTEGER,
        salary REAL,
        FOREIGN KEY (department_id) REFERENCES departments(id)
    )
    """
)
schema_toolkit.execute_query(
    """
    CREATE TABLE projects (
        id INTEGER PRIMARY KEY,
        name TEXT,
        employee_id INTEGER,
        FOREIGN KEY (employee_id) REFERENCES employees(id)
    )
    """
)
schema_toolkit.execute_query(
    "INSERT INTO departments VALUES (1, 'Engineering', 1000000.0)"
)
schema_toolkit.execute_query(
    "INSERT INTO employees VALUES (1, 'Alice', 1, 95000.0)"
)

# Method 1: List all tables using the toolkit method
tables = schema_toolkit.list_tables()
print("\nAll tables in database:")
print(tables)

'''
===============================================================================
All tables in database:
['departments', 'employees', 'projects']
===============================================================================
'''

# Method 2: Get table schema with primary and foreign keys
schema_info = schema_toolkit.get_table_info("employees")
print("\nSchema of 'employees' table (with primary and foreign keys):")
print(f"Table Name: {schema_info['table_name']}")
print(f"Columns: {schema_info['columns']}")
print(f"Primary Keys: {schema_info['primary_keys']}")
print(f"Foreign Keys: {schema_info['foreign_keys']}")
print(f"Row Count: {schema_info['row_count']}")

'''
===============================================================================
Schema of 'employees' table (with primary and foreign keys):
Columns: [{'column_name': 'id', 'column_type': 'INTEGER', ...}, ...]
Primary Keys: ['id']
Foreign Keys: [{'column': 'department_id', 'references_table': ...}]
===============================================================================
'''

# Method 3: Get comprehensive info for a specific table
table_info = schema_toolkit.get_table_info("employees")
print("\nComplete info for 'employees' table:")
print(f"Table: {table_info['table_name']}")
print(f"Primary Keys: {table_info['primary_keys']}")
print(f"Foreign Keys: {table_info['foreign_keys']}")
print(f"Row Count: {table_info['row_count']}")

'''
===============================================================================
Complete info for 'employees' table:
Table: employees
Primary Keys: ['id']
Foreign Keys: [{'column': 'department_id', 'references_table': ...}]
Row Count: 1
===============================================================================
'''

# Method 4: Get info for all tables at once (includes relationships)
all_tables_info = schema_toolkit.get_table_info()
print("\nInfo for all tables (with relationships):")
for table_name, info in all_tables_info.items():
    print(f"\n{table_name}:")
    print(f"  Primary Keys: {info['primary_keys']}")
    print(f"  Foreign Keys: {info['foreign_keys']}")
    print(f"  Row Count: {info['row_count']}")

'''
===============================================================================
Info for all tables (with relationships):
departments:
  Primary Keys: ['id']
  Foreign Keys: []
  Row Count: 1

employees:
  Primary Keys: ['id']
  Foreign Keys: [{'column': 'department_id', 'references_table': ...}]
  Row Count: 1

projects:
  Primary Keys: ['id']
  Foreign Keys: [{'column': 'employee_id', 'references_table': ...}]
  Row Count: 0
===============================================================================
'''

print("\n" + "=" * 80)
print("SQL Toolkit examples completed successfully!")
print("=" * 80)

# Example 11: Using SQL Toolkit with ChatAgent - Schema Discovery First
print("\n" + "=" * 80)
print("Example 11: Using SQL Toolkit with ChatAgent (with Schema Discovery)")
print("=" * 80)

# Create a model using OpenAI
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict=ChatGPTConfig(
        temperature=0.0,
    ).as_dict(),
)

# Create a new in-memory database for the agent
agent_sql_toolkit = SQLToolkit(database_path=":memory:", read_only=False)

# Set up initial data
agent_sql_toolkit.execute_query(
    "CREATE TABLE employees "
    "(id INTEGER, name TEXT, department TEXT, salary REAL)"
)
agent_sql_toolkit.execute_query(
    "INSERT INTO employees VALUES (1, 'Alice', 'Engineering', 95000.0)"
)
agent_sql_toolkit.execute_query(
    "INSERT INTO employees VALUES (2, 'Bob', 'Marketing', 75000.0)"
)
agent_sql_toolkit.execute_query(
    "INSERT INTO employees VALUES (3, 'Charlie', 'Engineering', 100000.0)"
)
agent_sql_toolkit.execute_query(
    "INSERT INTO employees VALUES (4, 'Diana', 'Sales', 80000.0)"
)

# Create a chat agent with the SQL toolkit
# Important: The agent can discover the schema using built-in methods!
agent = ChatAgent(
    system_message=(
        "You are a helpful database assistant. You can execute SQL queries "
        "to help users analyze and manage their data.\n\n"
        "IMPORTANT: Before answering questions about the data, you should "
        "first discover the database schema using these tools:\n"
        "1. Use 'list_tables' to list all tables in the database\n"
        "2. Use 'get_table_info' with a table name to get comprehensive "
        "info including schema (columns, primary keys, foreign keys) and "
        "row counts\n"
        "   - Call with a table name for specific table info\n"
        "   - Call without arguments to get info for all tables\n\n"
        "The schema information includes primary keys and foreign key "
        "relationships, which will help you write correct JOIN queries.\n\n"
        "After understanding the schema, you can write appropriate SQL "
        "queries using 'execute_query' to answer user questions."
    ),
    model=model,
    tools=[*agent_sql_toolkit.get_tools()],
)

# Example: Agent discovers schema first, then answers question
print("\nUser: What tables are in the database and what's their structure?")
response_schema = agent.step(
    "What tables are in the database and what's their structure?"
)
print(f"Agent: {response_schema.msgs[0].content}")

# Now the agent knows the schema, it can answer questions
print("\nUser: What is the average salary by department?")
response1 = agent.step("What is the average salary by department?")
print(f"Agent: {response1.msgs[0].content}")

'''
===============================================================================
User: What tables are in the database and what's their structure?
Agent: I'll first discover the database schema using the built-in
schema discovery tools.

[Agent calls: list_tables()]
[Agent calls: get_table_info("employees")]

The database contains the following table:
- employees:
  * Columns: id (INTEGER), name (TEXT), department (TEXT), salary (REAL)
  * Primary Keys: []
  * Foreign Keys: []

Now I understand the schema and can answer questions about the data.

User: What is the average salary by department?
Agent: I'll query the database to find the average salary by department.

[Agent executes SQL query:
 SELECT department, AVG(salary) as avg_salary FROM employees GROUP BY dept]

Here are the average salaries by department:

| Department   | Average Salary |
|--------------|----------------|
| Engineering  | $97,500.00     |
| Marketing    | $75,000.00     |
| Sales        | $80,000.00     |

The Engineering department has the highest average salary at $97,500.
===============================================================================
'''

# Example query: Find employees in Engineering
print("\nUser: Show me all employees in the Engineering department.")
response2 = agent.step("Show me all employees in the Engineering department.")
print(f"Agent: {response2.msgs[0].content}")

'''
===============================================================================
User: Show me all employees in the Engineering department.
Agent: I'll query the database to find all Engineering employees.

[Agent executes SQL query:
 SELECT * FROM employees WHERE department = 'Engineering']

Here are all employees in the Engineering department:

| ID | Name    | Department  | Salary   |
|----|---------|-------------|----------|
| 1  | Alice   | Engineering | $95,000  |
| 3  | Charlie | Engineering | $100,000 |

There are 2 employees in the Engineering department.
===============================================================================
'''

# Example query: Add a new employee
print(
    "\nUser: Add a new employee named Eve to the Sales department "
    "with a salary of 85000."
)
response3 = agent.step(
    "Add a new employee named Eve to the Sales department "
    "with a salary of 85000."
)
print(f"Agent: {response3.msgs[0].content}")

# Verify the new employee was added
print("\nUser: Show me all employees in Sales now.")
response4 = agent.step("Show me all employees in Sales now.")
print(f"Agent: {response4.msgs[0].content}")

'''
===============================================================================
User: Add a new employee named Eve to the Sales department with salary 85000.
Agent: I'll add the new employee to the database.

[Agent executes SQL query: INSERT INTO employees (name, department, salary)
VALUES ('Eve', 'Sales', 85000.0)]

The new employee Eve has been successfully added to the Sales department
with a salary of $85,000.

User: Show me all employees in Sales now.
Agent: I'll query the database to show all employees in the Sales department.

[Agent executes SQL query: SELECT * FROM employees WHERE department = 'Sales']

Here are all employees in the Sales department:

| ID | Name  | Department | Salary   |
|----|-------|------------|----------|
| 4  | Diana | Sales      | $80,000  |
| 5  | Eve   | Sales      | $85,000  |

There are now 2 employees in the Sales department.
===============================================================================
'''

# Example 12: Agent with Read-Only SQL Toolkit
print("\n" + "=" * 80)
print("Example 12: Agent with Read-Only SQL Toolkit")
print("=" * 80)

# Create a read-only toolkit (after setting up data)
readonly_agent_toolkit = SQLToolkit(database_path=":memory:", read_only=False)
readonly_agent_toolkit.execute_query(
    "CREATE TABLE products (id INTEGER, name TEXT, price REAL, stock INTEGER)"
)
readonly_agent_toolkit.execute_query(
    "INSERT INTO products VALUES (1, 'Widget', 19.99, 100)"
)
readonly_agent_toolkit.execute_query(
    "INSERT INTO products VALUES (2, 'Gadget', 29.99, 50)"
)
readonly_agent_toolkit.read_only = True  # Switch to read-only mode

readonly_agent = ChatAgent(
    system_message=(
        "You are a helpful database assistant in read-only mode. You can "
        "only query data, not modify it.\n\n"
        "IMPORTANT: Before answering questions, you should discover the "
        "database schema using these tools:\n"
        "1. Use 'list_tables' to list all tables\n"
        "2. Use 'get_table_info' to get comprehensive table information "
        "including schema (columns, primary keys, foreign keys) and row "
        "counts\n"
        "   - Call with a table name for specific table info\n"
        "   - Call without arguments to get info for all tables\n\n"
        "After understanding the schema, use 'execute_query' to run SELECT "
        "queries only. Write operations (INSERT, UPDATE, DELETE, etc.) are "
        "not allowed in read-only mode."
    ),
    model=model,
    tools=[*readonly_agent_toolkit.get_tools()],
)

print("\nUser: What products do we have in stock?")
response5 = readonly_agent.step("What products do we have in stock?")
print(f"Agent: {response5.msgs[0].content}")

print("\nUser: Try to add a new product called 'Thingamajig' for $39.99.")
response6 = readonly_agent.step(
    "Try to add a new product called 'Thingamajig' for $39.99."
)
print(f"Agent: {response6.msgs[0].content}")

'''
===============================================================================
User: What products do we have in stock?
Agent: I'll first discover the database schema, then query the products.

[Agent calls: list_tables()]
[Agent calls: get_table_info("products")]
[Agent executes SQL query: SELECT * FROM products]

Here are all products in stock:

| ID | Name   | Price  | Stock |
|----|--------|--------|-------|
| 1  | Widget | $19.99 | 100   |
| 2  | Gadget | $29.99 | 50    |

User: Try to add a new product called 'Thingamajig' for $39.99.
Agent: I'm in read-only mode, so I cannot modify the database. I can only
query existing data. If you need to add a product, please use a database
connection with write permissions.

[Agent attempts to execute INSERT query but it's blocked by read-only mode]
===============================================================================
'''

print("\n" + "=" * 80)
print("All SQL Toolkit examples completed successfully!")
print("=" * 80)
