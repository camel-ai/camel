# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========

import os
import tempfile
from pathlib import Path

import pytest

from camel.toolkits import SQLToolkit


@pytest.fixture
def sql_toolkit_memory():
    r"""Create a SQLToolkit instance with in-memory database."""
    toolkit = SQLToolkit(database_path=":memory:", read_only=False)
    yield toolkit
    # Cleanup is handled by __del__


@pytest.fixture
def sql_toolkit_readonly():
    r"""Create a SQLToolkit instance in read-only mode."""
    # First create toolkit in read-write mode to set up test data
    toolkit = SQLToolkit(database_path=":memory:", read_only=False)
    # Set up some test data first
    toolkit.execute_query("CREATE TABLE users (id INTEGER, name TEXT)")
    toolkit.execute_query("INSERT INTO users VALUES (1, 'Alice')")
    toolkit.execute_query("INSERT INTO users VALUES (2, 'Bob')")
    # Switch to read-only mode
    toolkit.read_only = True
    yield toolkit


@pytest.fixture
def sql_toolkit_sqlite():
    r"""Create a SQLToolkit instance with SQLite in-memory database."""
    toolkit = SQLToolkit(
        database_path=":memory:", database_type="sqlite", read_only=False
    )
    yield toolkit
    # Cleanup is handled by __del__


@pytest.fixture
def sql_toolkit_file():
    r"""Create a SQLToolkit instance with file-based database."""
    # Create a temporary file path
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name
    # Close and remove the empty file so DuckDB can create a new database
    try:
        Path(db_path).unlink()
    except Exception:
        pass

    toolkit = SQLToolkit(database_path=db_path, read_only=False)
    yield toolkit

    # Cleanup
    try:
        toolkit._connection.close()
    except Exception:
        pass
    try:
        Path(db_path).unlink()
    except Exception:
        pass


def test_initialization_default():
    r"""Test the initialization of SQLToolkit with default parameters."""
    toolkit = SQLToolkit()

    assert toolkit.database_type in SQLToolkit._SUPPORTED_DATABASES
    assert toolkit.read_only is False
    assert toolkit.timeout == 180.0
    assert toolkit._connection is not None


def test_initialization_with_custom_parameters():
    r"""Test the initialization of SQLToolkit with custom parameters."""
    toolkit = SQLToolkit(
        database_path=":memory:",
        database_type="duckdb",
        read_only=True,
        timeout=30.0,
    )

    assert toolkit.database_type in SQLToolkit._SUPPORTED_DATABASES
    assert toolkit.read_only is True
    assert toolkit.timeout == 30.0
    assert toolkit._connection is not None


def test_initialization_invalid_database_type():
    r"""Test that initialization fails with unsupported database type."""
    with pytest.raises(ValueError, match="Unsupported database_type"):
        SQLToolkit(database_type="postgresql")


def test_create_table(sql_toolkit_memory):
    r"""Test creating a table in read-write mode."""
    result = sql_toolkit_memory.execute_query(
        "CREATE TABLE users (id INTEGER, name TEXT)"
    )
    assert isinstance(result, dict)
    assert result["status"] == "success"


def test_insert_data(sql_toolkit_memory):
    r"""Test inserting data in read-write mode."""
    # Create table first
    sql_toolkit_memory.execute_query(
        "CREATE TABLE users (id INTEGER, name TEXT)"
    )
    # Insert data
    result = sql_toolkit_memory.execute_query(
        "INSERT INTO users VALUES (1, 'Alice')"
    )
    assert isinstance(result, dict)
    assert result["status"] == "success"
    assert "message" in result


def test_select_query(sql_toolkit_memory):
    r"""Test SELECT query execution."""
    # Set up test data
    sql_toolkit_memory.execute_query(
        "CREATE TABLE users (id INTEGER, name TEXT)"
    )
    sql_toolkit_memory.execute_query("INSERT INTO users VALUES (1, 'Alice')")
    sql_toolkit_memory.execute_query("INSERT INTO users VALUES (2, 'Bob')")

    # Execute SELECT query
    results = sql_toolkit_memory.execute_query("SELECT * FROM users")

    assert len(results) == 2
    assert results[0]["id"] == 1
    assert results[0]["name"] == "Alice"
    assert results[1]["id"] == 2
    assert results[1]["name"] == "Bob"


def test_select_with_where(sql_toolkit_memory):
    r"""Test SELECT query with WHERE clause."""
    # Set up test data
    sql_toolkit_memory.execute_query(
        "CREATE TABLE users (id INTEGER, name TEXT)"
    )
    sql_toolkit_memory.execute_query("INSERT INTO users VALUES (1, 'Alice')")
    sql_toolkit_memory.execute_query("INSERT INTO users VALUES (2, 'Bob')")

    # Execute SELECT with WHERE
    results = sql_toolkit_memory.execute_query(
        "SELECT * FROM users WHERE id = 1"
    )

    assert len(results) == 1
    assert results[0]["id"] == 1
    assert results[0]["name"] == "Alice"


def test_select_empty_result(sql_toolkit_memory):
    r"""Test SELECT query that returns no results."""
    # Create empty table
    sql_toolkit_memory.execute_query(
        "CREATE TABLE users (id INTEGER, name TEXT)"
    )

    # Execute SELECT on empty table
    results = sql_toolkit_memory.execute_query("SELECT * FROM users")

    assert results == []


def test_update_query(sql_toolkit_memory):
    r"""Test UPDATE query in read-write mode."""
    # Set up test data
    sql_toolkit_memory.execute_query(
        "CREATE TABLE users (id INTEGER, name TEXT)"
    )
    sql_toolkit_memory.execute_query("INSERT INTO users VALUES (1, 'Alice')")

    # Update data
    result = sql_toolkit_memory.execute_query(
        "UPDATE users SET name = 'Alice Updated' WHERE id = 1"
    )
    assert isinstance(result, dict)
    assert result["status"] == "success"
    assert "message" in result

    # Verify update
    results = sql_toolkit_memory.execute_query("SELECT * FROM users")
    assert results[0]["name"] == "Alice Updated"


def test_delete_query(sql_toolkit_memory):
    r"""Test DELETE query in read-write mode."""
    # Set up test data
    sql_toolkit_memory.execute_query(
        "CREATE TABLE users (id INTEGER, name TEXT)"
    )
    sql_toolkit_memory.execute_query("INSERT INTO users VALUES (1, 'Alice')")
    sql_toolkit_memory.execute_query("INSERT INTO users VALUES (2, 'Bob')")

    # Delete data
    result = sql_toolkit_memory.execute_query("DELETE FROM users WHERE id = 1")
    assert isinstance(result, dict)
    assert result["status"] == "success"
    assert "message" in result

    # Verify deletion
    results = sql_toolkit_memory.execute_query("SELECT * FROM users")
    assert len(results) == 1
    assert results[0]["id"] == 2


def test_readonly_mode_allows_select(sql_toolkit_readonly):
    r"""Test that read-only mode allows SELECT queries."""
    results = sql_toolkit_readonly.execute_query("SELECT * FROM users")

    assert len(results) == 2
    assert results[0]["id"] == 1
    assert results[1]["id"] == 2


def test_readonly_mode_blocks_insert(sql_toolkit_readonly):
    r"""Test that read-only mode blocks INSERT queries."""
    result = sql_toolkit_readonly.execute_query(
        "INSERT INTO users VALUES (3, 'Charlie')"
    )
    assert isinstance(result, str)
    assert "Write operations are not allowed" in result


def test_readonly_mode_blocks_update(sql_toolkit_readonly):
    r"""Test that read-only mode blocks UPDATE queries."""
    result = sql_toolkit_readonly.execute_query(
        "UPDATE users SET name = 'Updated' WHERE id = 1"
    )
    assert isinstance(result, str)
    assert "Write operations are not allowed" in result


def test_readonly_mode_blocks_delete(sql_toolkit_readonly):
    r"""Test that read-only mode blocks DELETE queries."""
    result = sql_toolkit_readonly.execute_query(
        "DELETE FROM users WHERE id = 1"
    )
    assert isinstance(result, str)
    assert "Write operations are not allowed" in result


def test_readonly_mode_blocks_create(sql_toolkit_readonly):
    r"""Test that read-only mode blocks CREATE TABLE queries."""
    result = sql_toolkit_readonly.execute_query(
        "CREATE TABLE new_table (id INTEGER)"
    )
    assert isinstance(result, str)
    assert "Write operations are not allowed" in result


def test_readonly_mode_blocks_drop(sql_toolkit_memory):
    r"""Test that read-only mode blocks DROP queries."""
    # Set up test data
    sql_toolkit_memory.execute_query(
        "CREATE TABLE users (id INTEGER, name TEXT)"
    )

    # Switch to read-only mode
    sql_toolkit_memory.read_only = True

    result = sql_toolkit_memory.execute_query("DROP TABLE users")
    assert isinstance(result, str)
    assert "Write operations are not allowed" in result


def test_readonly_mode_blocks_alter(sql_toolkit_memory):
    r"""Test that read-only mode blocks ALTER queries."""
    # Set up test data
    sql_toolkit_memory.execute_query(
        "CREATE TABLE users (id INTEGER, name TEXT)"
    )

    # Switch to read-only mode
    sql_toolkit_memory.read_only = True

    result = sql_toolkit_memory.execute_query(
        "ALTER TABLE users ADD COLUMN email TEXT"
    )
    assert isinstance(result, str)
    assert "Write operations are not allowed" in result


def test_readonly_mode_blocks_truncate(sql_toolkit_memory):
    r"""Test that read-only mode blocks TRUNCATE queries."""
    # Set up test data
    sql_toolkit_memory.execute_query(
        "CREATE TABLE users (id INTEGER, name TEXT)"
    )

    # Switch to read-only mode
    sql_toolkit_memory.read_only = True

    result = sql_toolkit_memory.execute_query("TRUNCATE TABLE users")
    assert isinstance(result, str)
    assert "Write operations are not allowed" in result


def test_query_with_comments(sql_toolkit_memory):
    r"""Test that queries with comments are handled correctly."""
    # Set up test data
    sql_toolkit_memory.execute_query(
        "CREATE TABLE users (id INTEGER, name TEXT)"
    )
    sql_toolkit_memory.execute_query("INSERT INTO users VALUES (1, 'Alice')")

    # Query with single-line comment
    results = sql_toolkit_memory.execute_query(
        "SELECT * FROM users -- This is a comment"
    )
    assert len(results) == 1

    # Query with multi-line comment
    results = sql_toolkit_memory.execute_query(
        "SELECT * FROM users /* This is a multi-line comment */"
    )
    assert len(results) == 1


def test_query_case_insensitive_keywords(sql_toolkit_memory):
    r"""Test that write keyword detection is case-insensitive."""
    # Set up test data
    sql_toolkit_memory.execute_query(
        "CREATE TABLE users (id INTEGER, name TEXT)"
    )

    # Switch to read-only mode
    sql_toolkit_memory.read_only = True

    # Test lowercase insert
    result = sql_toolkit_memory.execute_query(
        "insert into users values (1, 'Alice')"
    )
    assert isinstance(result, str)
    assert "Write operations are not allowed" in result

    # Test mixed case update
    result = sql_toolkit_memory.execute_query(
        "UpDaTe users SET name = 'Bob' WHERE id = 1"
    )
    assert isinstance(result, str)
    assert "Write operations are not allowed" in result


def test_join_query(sql_toolkit_memory):
    r"""Test JOIN query execution."""
    # Set up test data with two tables
    sql_toolkit_memory.execute_query(
        "CREATE TABLE users (id INTEGER, name TEXT)"
    )
    sql_toolkit_memory.execute_query(
        "CREATE TABLE orders (id INTEGER, user_id INTEGER, amount REAL)"
    )
    sql_toolkit_memory.execute_query("INSERT INTO users VALUES (1, 'Alice')")
    sql_toolkit_memory.execute_query("INSERT INTO users VALUES (2, 'Bob')")
    sql_toolkit_memory.execute_query("INSERT INTO orders VALUES (1, 1, 100.0)")
    sql_toolkit_memory.execute_query("INSERT INTO orders VALUES (2, 1, 50.0)")

    # Execute JOIN query
    results = sql_toolkit_memory.execute_query(
        """
        SELECT u.name, o.amount
        FROM users u
        JOIN orders o ON u.id = o.user_id
        ORDER BY o.amount DESC
        """
    )

    assert len(results) == 2
    assert results[0]["name"] == "Alice"
    assert results[0]["amount"] == 100.0
    assert results[1]["name"] == "Alice"
    assert results[1]["amount"] == 50.0


def test_multiple_queries_sequence(sql_toolkit_memory):
    r"""Test executing multiple queries in sequence."""
    # Create table
    sql_toolkit_memory.execute_query(
        "CREATE TABLE users (id INTEGER, name TEXT)"
    )

    # Insert multiple rows
    sql_toolkit_memory.execute_query("INSERT INTO users VALUES (1, 'Alice')")
    sql_toolkit_memory.execute_query("INSERT INTO users VALUES (2, 'Bob')")
    sql_toolkit_memory.execute_query("INSERT INTO users VALUES (3, 'Charlie')")

    # Query all
    results = sql_toolkit_memory.execute_query("SELECT * FROM users")
    assert len(results) == 3

    # Update one
    sql_toolkit_memory.execute_query(
        "UPDATE users SET name = 'Bob Updated' WHERE id = 2"
    )

    # Query again
    results = sql_toolkit_memory.execute_query("SELECT * FROM users")
    assert len(results) == 3
    assert results[1]["name"] == "Bob Updated"


def test_invalid_query_syntax(sql_toolkit_memory):
    r"""Test handling of invalid SQL syntax."""
    result = sql_toolkit_memory.execute_query("INVALID SQL SYNTAX")
    assert isinstance(result, str)
    assert "Error:" in result


def test_empty_query(sql_toolkit_memory):
    r"""Test handling of empty query."""
    result = sql_toolkit_memory.execute_query("")
    assert isinstance(result, str)
    assert "Query cannot be empty" in result


def test_file_based_database(sql_toolkit_file):
    r"""Test file-based database persistence."""
    # Create table and insert data
    sql_toolkit_file.execute_query(
        "CREATE TABLE users (id INTEGER, name TEXT)"
    )
    sql_toolkit_file.execute_query("INSERT INTO users VALUES (1, 'Alice')")

    # Close connection
    sql_toolkit_file._connection.close()

    # Reopen connection to same file
    db_path = sql_toolkit_file.database_path
    new_toolkit = SQLToolkit(database_path=db_path, read_only=False)

    # Verify data persists
    results = new_toolkit.execute_query("SELECT * FROM users")
    assert len(results) == 1
    assert results[0]["id"] == 1
    assert results[0]["name"] == "Alice"

    # Cleanup
    new_toolkit._connection.close()


def test_file_based_duckdb_readonly_mode():
    r"""Test that file-based DuckDB connections pass read_only parameter."""
    import tempfile
    from pathlib import Path

    # Create a temporary file path
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name
    # Close and remove the empty file so DuckDB can create a new database
    try:
        Path(db_path).unlink()
    except Exception:
        pass

    try:
        # Create database and add data
        toolkit = SQLToolkit(
            database_path=db_path, database_type="duckdb", read_only=False
        )
        toolkit.execute_query("CREATE TABLE products (id INTEGER, name TEXT)")
        toolkit.execute_query("INSERT INTO products VALUES (1, 'Widget')")
        toolkit._connection.close()

        # Open in read-only mode - should pass read_only=True to duckdb
        readonly_toolkit = SQLToolkit(
            database_path=db_path, database_type="duckdb", read_only=True
        )

        # Should be able to read
        result = readonly_toolkit.execute_query("SELECT * FROM products")
        assert len(result) == 1
        assert result[0]["name"] == "Widget"

        # Should not be able to write (application-level check)
        result = readonly_toolkit.execute_query(
            "INSERT INTO products VALUES (2, 'Gadget')"
        )
        assert isinstance(result, str)
        assert "Write operations are not allowed" in result

        # The read_only parameter should also be passed to duckdb.connect(),
        # providing database-level protection. If we try to write directly
        # through the connection, DuckDB should also block it.
        # However, our application-level check catches it first, so this test
        # primarily verifies that the parameter is passed correctly.

        readonly_toolkit._connection.close()
    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_get_tools(sql_toolkit_memory):
    r"""Test that get_tools returns the correct function tools."""
    tools = sql_toolkit_memory.get_tools()

    assert len(tools) == 3
    tool_names = [tool.get_function_name() for tool in tools]
    assert "execute_query" in tool_names
    assert "list_tables" in tool_names
    assert "get_table_info" in tool_names


def test_list_tables(sql_toolkit_memory):
    r"""Test listing all tables in the database."""
    # Create some tables
    sql_toolkit_memory.execute_query(
        "CREATE TABLE users (id INTEGER, name TEXT)"
    )
    sql_toolkit_memory.execute_query(
        "CREATE TABLE orders (id INTEGER, user_id INTEGER)"
    )

    tables = sql_toolkit_memory.list_tables()
    assert isinstance(tables, list)
    assert "users" in tables
    assert "orders" in tables


def test_list_tables_empty(sql_toolkit_memory):
    r"""Test listing tables when database is empty."""
    tables = sql_toolkit_memory.list_tables()
    assert tables == []


def test_describe_table(sql_toolkit_memory):
    r"""Test describing a table schema."""
    # Create a table
    sql_toolkit_memory.execute_query(
        "CREATE TABLE users (id INTEGER, name TEXT, age INTEGER)"
    )

    schema_info = sql_toolkit_memory.get_table_info("users")
    assert isinstance(schema_info, dict)
    assert "table_name" in schema_info
    assert "row_count" in schema_info
    assert "columns" in schema_info
    assert "primary_keys" in schema_info
    assert "foreign_keys" in schema_info
    assert schema_info["table_name"] == "users"

    columns = schema_info["columns"]
    assert isinstance(columns, list)
    assert len(columns) == 3

    # Check column names
    column_names = [col["column_name"] for col in columns]
    assert "id" in column_names
    assert "name" in column_names
    assert "age" in column_names

    # Check primary keys (should be empty for this table)
    assert schema_info["primary_keys"] == []
    assert schema_info["foreign_keys"] == []


def test_describe_table_nonexistent(sql_toolkit_memory):
    r"""Test getting info for a non-existent table."""
    result = sql_toolkit_memory.get_table_info("nonexistent_table")
    assert isinstance(result, str)
    assert "Error:" in result


def test_describe_table_empty_name(sql_toolkit_memory):
    r"""Test getting info for a table with empty name."""
    result = sql_toolkit_memory.get_table_info("")
    assert isinstance(result, str)
    assert "Table name cannot be empty" in result


def test_get_table_info_specific_table(sql_toolkit_memory):
    r"""Test getting info for a specific table."""
    # Create and populate a table
    sql_toolkit_memory.execute_query(
        "CREATE TABLE users (id INTEGER, name TEXT)"
    )
    sql_toolkit_memory.execute_query("INSERT INTO users VALUES (1, 'Alice')")
    sql_toolkit_memory.execute_query("INSERT INTO users VALUES (2, 'Bob')")

    info = sql_toolkit_memory.get_table_info("users")
    assert info["table_name"] == "users"
    assert info["row_count"] == 2
    assert "columns" in info
    assert "primary_keys" in info
    assert "foreign_keys" in info
    assert len(info["columns"]) == 2


def test_get_table_info_all_tables(sql_toolkit_memory):
    r"""Test getting info for all tables."""
    # Create multiple tables
    sql_toolkit_memory.execute_query(
        "CREATE TABLE users (id INTEGER, name TEXT)"
    )
    sql_toolkit_memory.execute_query(
        "CREATE TABLE orders (id INTEGER, amount REAL)"
    )
    sql_toolkit_memory.execute_query("INSERT INTO users VALUES (1, 'Alice')")

    info = sql_toolkit_memory.get_table_info()
    assert isinstance(info, dict)
    assert "users" in info
    assert "orders" in info
    assert info["users"]["row_count"] == 1
    assert info["orders"]["row_count"] == 0
    assert "primary_keys" in info["users"]
    assert "foreign_keys" in info["users"]


def test_schema_discovery_readonly_mode(sql_toolkit_memory):
    r"""Test that schema discovery methods work in read-only mode."""
    # Set up data
    sql_toolkit_memory.execute_query(
        "CREATE TABLE users (id INTEGER, name TEXT)"
    )
    sql_toolkit_memory.execute_query("INSERT INTO users VALUES (1, 'Alice')")

    # Switch to read-only mode
    sql_toolkit_memory.read_only = True

    # Schema discovery should work in read-only mode
    tables = sql_toolkit_memory.list_tables()
    assert "users" in tables

    schema_info = sql_toolkit_memory.get_table_info("users")
    assert isinstance(schema_info, dict)
    assert len(schema_info["columns"]) == 2

    info = sql_toolkit_memory.get_table_info("users")
    assert info["table_name"] == "users"


def test_describe_table_with_primary_key(sql_toolkit_memory):
    r"""Test getting info for a table with primary key."""
    # Create a table with primary key
    sql_toolkit_memory.execute_query(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)"
    )

    schema_info = sql_toolkit_memory.get_table_info("users")
    assert "primary_keys" in schema_info
    assert "id" in schema_info["primary_keys"]
    assert len(schema_info["primary_keys"]) == 1


def test_describe_table_with_foreign_key(sql_toolkit_memory):
    r"""Test describing a table with foreign key."""
    # Create parent table
    sql_toolkit_memory.execute_query(
        "CREATE TABLE departments (id INTEGER PRIMARY KEY, name TEXT)"
    )
    # Create child table with foreign key
    sql_toolkit_memory.execute_query(
        """
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            name TEXT,
            department_id INTEGER,
            FOREIGN KEY (department_id) REFERENCES departments(id)
        )
        """
    )

    schema_info = sql_toolkit_memory.get_table_info("employees")
    assert "foreign_keys" in schema_info
    assert len(schema_info["foreign_keys"]) == 1
    fk = schema_info["foreign_keys"][0]
    assert fk["column"] == "department_id"
    assert fk["references_table"] == "departments"
    assert fk["references_column"] == "id"


def test_query_with_whitespace(sql_toolkit_memory):
    r"""Test that queries with extra whitespace are handled correctly."""
    # Set up test data
    sql_toolkit_memory.execute_query(
        "CREATE TABLE users (id INTEGER, name TEXT)"
    )
    sql_toolkit_memory.execute_query("INSERT INTO users VALUES (1, 'Alice')")

    # Query with extra whitespace
    results = sql_toolkit_memory.execute_query(
        "   SELECT   *   FROM   users   "
    )

    assert len(results) == 1
    assert results[0]["id"] == 1


def test_select_star_vs_specific_columns(sql_toolkit_memory):
    r"""Test SELECT with specific columns vs SELECT *."""
    # Set up test data
    sql_toolkit_memory.execute_query(
        "CREATE TABLE users (id INTEGER, name TEXT, email TEXT)"
    )
    sql_toolkit_memory.execute_query(
        "INSERT INTO users VALUES (1, 'Alice', 'alice@example.com')"
    )

    # SELECT *
    results_all = sql_toolkit_memory.execute_query("SELECT * FROM users")
    assert len(results_all[0]) == 3
    assert "id" in results_all[0]
    assert "name" in results_all[0]
    assert "email" in results_all[0]

    # SELECT specific columns
    results_specific = sql_toolkit_memory.execute_query(
        "SELECT id, name FROM users"
    )
    assert len(results_specific[0]) == 2
    assert "id" in results_specific[0]
    assert "name" in results_specific[0]
    assert "email" not in results_specific[0]


def test_cte_query(sql_toolkit_memory):
    r"""Test Common Table Expression (CTE) queries that start with WITH."""
    # Set up test data
    sql_toolkit_memory.execute_query(
        "CREATE TABLE users (id INTEGER, name TEXT, age INTEGER)"
    )
    sql_toolkit_memory.execute_query(
        "INSERT INTO users VALUES (1, 'Alice', 25)"
    )
    sql_toolkit_memory.execute_query("INSERT INTO users VALUES (2, 'Bob', 30)")
    sql_toolkit_memory.execute_query(
        "INSERT INTO users VALUES (3, 'Charlie', 25)"
    )

    # CTE query that starts with WITH, not SELECT
    results = sql_toolkit_memory.execute_query(
        """
        WITH adults AS (
            SELECT * FROM users WHERE age >= 25
        )
        SELECT * FROM adults
        """
    )

    assert len(results) == 3
    assert all(row["age"] >= 25 for row in results)


def test_explain_query(sql_toolkit_memory):
    r"""Test EXPLAIN queries that start with EXPLAIN, not SELECT."""
    # Set up test data
    sql_toolkit_memory.execute_query(
        "CREATE TABLE users (id INTEGER, name TEXT)"
    )
    sql_toolkit_memory.execute_query("INSERT INTO users VALUES (1, 'Alice')")

    # EXPLAIN query returns results but doesn't start with SELECT
    results = sql_toolkit_memory.execute_query("EXPLAIN SELECT * FROM users")

    # EXPLAIN should return results (query plan)
    assert isinstance(results, list)
    # Results should have at least one row with query plan information
    assert len(results) > 0


def test_cte_with_join(sql_toolkit_memory):
    r"""Test CTE queries with JOIN operations."""
    # Set up test data
    sql_toolkit_memory.execute_query(
        "CREATE TABLE users (id INTEGER, name TEXT)"
    )
    sql_toolkit_memory.execute_query(
        "CREATE TABLE orders (id INTEGER, user_id INTEGER, amount REAL)"
    )
    sql_toolkit_memory.execute_query("INSERT INTO users VALUES (1, 'Alice')")
    sql_toolkit_memory.execute_query("INSERT INTO orders VALUES (1, 1, 100.0)")
    sql_toolkit_memory.execute_query("INSERT INTO orders VALUES (2, 1, 50.0)")

    # CTE with JOIN
    results = sql_toolkit_memory.execute_query(
        """
        WITH user_orders AS (
            SELECT u.name, o.amount
            FROM users u
            JOIN orders o ON u.id = o.user_id
        )
        SELECT * FROM user_orders
        """
    )

    assert len(results) == 2
    assert results[0]["name"] == "Alice"
    assert results[0]["amount"] == 100.0
    assert results[1]["amount"] == 50.0


def test_sql_injection_protection_table_name(sql_toolkit_memory):
    r"""Test that table names are properly quoted to prevent SQL injection."""
    # Create a normal table
    sql_toolkit_memory.execute_query(
        "CREATE TABLE users (id INTEGER, name TEXT)"
    )
    sql_toolkit_memory.execute_query("INSERT INTO users VALUES (1, 'Alice')")

    # Try to inject SQL through table name
    # This should be safely quoted and not execute the injected SQL
    malicious_table_name = "users; DROP TABLE users; --"

    # This should return an error because the table doesn't exist
    # (the malicious SQL should be treated as part of the table name)
    result = sql_toolkit_memory.get_table_info(malicious_table_name)
    assert isinstance(result, str)
    assert "Error:" in result

    # Verify the original table still exists (wasn't dropped)
    tables = sql_toolkit_memory.list_tables()
    assert "users" in tables

    # Test with table name containing quotes
    table_with_quotes = 'table"name'
    sql_toolkit_memory.execute_query('CREATE TABLE "table""name" (id INTEGER)')
    # Should work correctly with quoted identifier
    schema = sql_toolkit_memory.get_table_info(table_with_quotes)
    # get_table_info returns a dict with table info
    assert "columns" in schema
    assert "table_name" in schema
    assert len(schema["columns"]) > 0

    # Test with table name containing special characters
    table_special = "table_name_123"
    sql_toolkit_memory.execute_query(
        'CREATE TABLE "table_name_123" (id INTEGER)'
    )
    schema = sql_toolkit_memory.get_table_info(table_special)
    # get_table_info returns a dict with table info
    assert "columns" in schema
    assert "table_name" in schema
    assert len(schema["columns"]) > 0


def test_quote_identifier_method(sql_toolkit_memory):
    r"""Test the _quote_identifier helper method."""
    # Test normal identifier
    assert sql_toolkit_memory._quote_identifier("users") == '"users"'

    # Test identifier with quotes (should be escaped)
    assert (
        sql_toolkit_memory._quote_identifier('table"name') == '"table""name"'
    )

    # Test identifier with spaces
    assert sql_toolkit_memory._quote_identifier("table name") == '"table name"'

    # Test empty identifier (should raise error)
    with pytest.raises(ValueError):
        sql_toolkit_memory._quote_identifier("")

    # Test identifier with null bytes (should raise error)
    with pytest.raises(ValueError):
        sql_toolkit_memory._quote_identifier("table\x00name")


def test_sqlite_basic_operations(sql_toolkit_sqlite):
    r"""Test basic SQLite operations."""
    # Create table
    sql_toolkit_sqlite.execute_query(
        "CREATE TABLE users (id INTEGER, name TEXT, age INTEGER)"
    )

    # Insert data - SQLite supports rows_affected
    insert_result = sql_toolkit_sqlite.execute_query(
        "INSERT INTO users VALUES (1, 'Alice', 25)"
    )
    assert isinstance(insert_result, dict)
    assert insert_result["status"] == "success"
    assert insert_result["rows_affected"] == 1

    # Query data
    result = sql_toolkit_sqlite.execute_query("SELECT * FROM users")
    assert len(result) == 1
    assert result[0]["id"] == 1
    assert result[0]["name"] == "Alice"
    assert result[0]["age"] == 25

    # Update data - SQLite supports rows_affected
    update_result = sql_toolkit_sqlite.execute_query(
        "UPDATE users SET age = 26 WHERE id = 1"
    )
    assert isinstance(update_result, dict)
    assert update_result["status"] == "success"
    assert update_result["rows_affected"] == 1


def test_sqlite_list_tables(sql_toolkit_sqlite):
    r"""Test listing tables in SQLite."""
    sql_toolkit_sqlite.execute_query("CREATE TABLE table1 (id INTEGER)")
    sql_toolkit_sqlite.execute_query("CREATE TABLE table2 (id INTEGER)")

    tables = sql_toolkit_sqlite.list_tables()
    assert "table1" in tables
    assert "table2" in tables


def test_sqlite_schema_discovery(sql_toolkit_sqlite):
    r"""Test schema discovery in SQLite."""
    sql_toolkit_sqlite.execute_query(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)"
    )

    schema_info = sql_toolkit_sqlite.get_table_info("users")
    assert "columns" in schema_info
    assert "primary_keys" in schema_info
    assert "id" in schema_info["primary_keys"]
    assert len(schema_info["columns"]) == 3


def test_sqlite_foreign_keys(sql_toolkit_sqlite):
    r"""Test foreign key discovery in SQLite."""
    sql_toolkit_sqlite.execute_query(
        "CREATE TABLE departments (id INTEGER PRIMARY KEY, name TEXT)"
    )
    sql_toolkit_sqlite.execute_query(
        """
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            name TEXT,
            department_id INTEGER,
            FOREIGN KEY (department_id) REFERENCES departments(id)
        )
        """
    )

    schema_info = sql_toolkit_sqlite.get_table_info("employees")
    assert "foreign_keys" in schema_info
    assert len(schema_info["foreign_keys"]) == 1
    fk = schema_info["foreign_keys"][0]
    assert fk["column"] == "department_id"
    assert fk["references_table"] == "departments"
    assert fk["references_column"] == "id"


def test_sqlite_readonly_mode():
    r"""Test SQLite read-only mode."""
    import os
    import tempfile

    # Create a temporary database file
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name

    try:
        # Create database and add data
        toolkit = SQLToolkit(
            database_path=db_path, database_type="sqlite", read_only=False
        )
        toolkit.execute_query("CREATE TABLE products (id INTEGER, name TEXT)")
        toolkit.execute_query("INSERT INTO products VALUES (1, 'Widget')")
        toolkit._connection.close()

        # Open in read-only mode
        readonly_toolkit = SQLToolkit(
            database_path=db_path, database_type="sqlite", read_only=True
        )

        # Should be able to read
        result = readonly_toolkit.execute_query("SELECT * FROM products")
        assert len(result) == 1

        # Should not be able to write
        result = readonly_toolkit.execute_query(
            "INSERT INTO products VALUES (2, 'Gadget')"
        )
        assert isinstance(result, str)
        assert "Write operations are not allowed" in result

        readonly_toolkit._connection.close()
    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
