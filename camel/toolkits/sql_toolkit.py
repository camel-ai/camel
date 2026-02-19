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

import re
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    List,
    Literal,
    Optional,
    Union,
)

from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import MCPServer

if TYPE_CHECKING:
    import sqlite3

    import duckdb

logger = get_logger(__name__)


@MCPServer()
class SQLToolkit(BaseToolkit):
    r"""A toolkit for executing SQL queries against various SQL databases.

    This toolkit provides functionality to execute SQL queries with support
    for read-only and read-write modes. It currently supports DuckDB and
    SQLite, with extensibility for MySQL and other SQL databases.

    Args:
        database_path (Optional[str]): Path to the database file. If None,
            uses an in-memory database. For DuckDB and SQLite, use ":memory:"
            for in-memory or a file path for persistent storage.
            (default: :obj:`None`)
        database_type (Literal["duckdb", "sqlite"]): Type of database to use.
            Currently supports "duckdb" and "sqlite".
            (default: :obj:`"duckdb"`)
        read_only (bool, optional): If True, only SELECT queries are allowed.
            Write operations (INSERT, UPDATE, DELETE, etc.) will be rejected.
            (default: :obj:`False`)
        timeout (Optional[float], optional): The timeout for database
            operations in seconds. Defaults to 180 seconds if not specified.
            (default: :obj:`180.0`)

    Raises:
        ValueError: If database_type is not supported.
        ImportError: If required database driver is not installed.
    """

    # SQL keywords that indicate write operations
    _WRITE_KEYWORDS: ClassVar[List[str]] = [
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "CREATE",
        "ALTER",
        "TRUNCATE",
        "REPLACE",
        "MERGE",
        "GRANT",
        "REVOKE",
        "COPY",
        "ATTACH",
        "DETACH",
        "LOAD",
        "IMPORT",
        "EXPORT",
    ]

    # Supported database types
    _SUPPORTED_DATABASES: ClassVar[List[str]] = ["duckdb", "sqlite"]

    def __init__(
        self,
        database_path: Optional[str] = None,
        database_type: Literal["duckdb", "sqlite"] = "duckdb",
        read_only: bool = False,
        timeout: Optional[float] = 180.0,
    ) -> None:
        super().__init__(timeout=timeout)
        self._validate_database_type(database_type)

        self.database_path = database_path
        self.database_type = database_type.lower()
        self.read_only = read_only

        # Initialize database connection
        self._connection = self._create_connection()

        logger.info(
            f"Initialized SQL toolkit with database_type: {database_type}, "
            f"database_path: {database_path or ':memory:'}, "
            f"read_only: {read_only}, timeout: {self.timeout}s"
        )

    def _validate_database_type(self, database_type: str) -> None:
        r"""Validate if the database type is supported.

        Args:
            database_type (str): The database type to validate.

        Raises:
            ValueError: If the database type is not supported.
        """
        if database_type.lower() not in self._SUPPORTED_DATABASES:
            raise ValueError(
                f"Unsupported database_type: {database_type}. "
                f"Supported types: {self._SUPPORTED_DATABASES}"
            )

    def _create_connection(
        self,
    ) -> "Union[duckdb.DuckDBPyConnection, sqlite3.Connection]":
        r"""Create a database connection based on the database type.

        Returns:
            Union[duckdb.DuckDBPyConnection, sqlite3.Connection]: A database
                connection object.

        Raises:
            ImportError: If the required database driver is not installed.
        """
        if self.database_type == "duckdb":
            try:
                import duckdb
            except ImportError:
                raise ImportError(
                    "duckdb package is required for DuckDB support. "
                    "Install it with: pip install duckdb"
                )

            if self.database_path is None or self.database_path == ":memory:":
                return duckdb.connect(":memory:")
            else:
                # Pass read_only parameter for file-based connections
                # This provides database-level protection in addition to
                # application-level checks
                return duckdb.connect(
                    self.database_path, read_only=self.read_only
                )
        elif self.database_type == "sqlite":
            try:
                import sqlite3
            except ImportError:
                raise ImportError(
                    "sqlite3 module is required for SQLite support. "
                    "It should be included with Python, but if missing, "
                    "ensure you're using a standard Python installation."
                )

            if self.database_path is None or self.database_path == ":memory:":
                conn = sqlite3.connect(":memory:", check_same_thread=False)
            else:
                # SQLite read-only mode using URI
                if self.read_only:
                    uri = f"file:{self.database_path}?mode=ro"
                    conn = sqlite3.connect(
                        uri, uri=True, check_same_thread=False
                    )
                else:
                    conn = sqlite3.connect(
                        self.database_path, check_same_thread=False
                    )

            # Enable row factory to return dict-like rows
            conn.row_factory = sqlite3.Row
            return conn
        else:
            raise ValueError(
                f"Unsupported database type: {self.database_type}"
            )

    def _is_write_query(self, query: str) -> bool:
        r"""Check if a SQL query is a write operation.

        This method analyzes the query string to determine if it contains
        any write operations. It handles comments and case-insensitive
        matching.

        Args:
            query (str): The SQL query to check.

        Returns:
            bool: True if the query is a write operation, False otherwise.
        """
        # Remove SQL comments (-- and /* */ style)
        # Remove single-line comments
        query_no_comments = re.sub(r"--.*$", "", query, flags=re.MULTILINE)
        # Remove multi-line comments
        query_no_comments = re.sub(
            r"/\*.*?\*/", "", query_no_comments, flags=re.DOTALL
        )

        # Normalize whitespace and convert to uppercase for keyword matching
        query_normalized = " ".join(query_no_comments.split()).upper()

        # Check for write keywords at the start of the query (after whitespace)
        for keyword in self._WRITE_KEYWORDS:
            # Match keyword at start of query or after whitespace/semicolon
            pattern = r"(^|\s|;)" + re.escape(keyword) + r"(\s|$)"
            if re.search(pattern, query_normalized):
                return True

        return False

    def _quote_identifier(self, identifier: str) -> str:
        r"""Safely quote a SQL identifier (table name, column name, etc.).

        This method validates and quotes SQL identifiers to prevent SQL
        injection. For DuckDB, identifiers are quoted with double quotes. Any
        double quotes within the identifier are escaped by doubling them.

        Args:
            identifier (str): The identifier to quote (e.g., table name,
                column name).

        Returns:
            str: The safely quoted identifier.

        Raises:
            ValueError: If the identifier is empty or contains invalid
                characters.
        """
        if not identifier or not identifier.strip():
            raise ValueError("Identifier cannot be empty")

        identifier = identifier.strip()

        # Validate identifier doesn't contain null bytes or other
        # dangerous characters
        if "\x00" in identifier:
            raise ValueError("Identifier cannot contain null bytes")

        # Escape double quotes by doubling them, then wrap in double quotes
        escaped = identifier.replace('"', '""')
        return f'"{escaped}"'

    def execute_query(
        self,
        query: str,
        params: Optional[
            Union[
                List[Union[str, int, float, bool, None]],
                Dict[str, Union[str, int, float, bool, None]],
            ]
        ] = None,
    ) -> Union[List[Dict[str, Any]], Dict[str, Any], str]:
        r"""Execute a SQL query and return results.

        This method executes a SQL query against the configured database and
        returns the results. For SELECT queries, returns a list of dictionaries
        where each dictionary represents a row. For write operations (INSERT,
        UPDATE, DELETE, etc.), returns a status dictionary with execution info.

        Args:
            query (str): The SQL query to execute.
            params (Optional[Union[List[Union[str, int, float, bool, None]],
                Dict[str, Union[str, int, float, bool, None]]]], optional):
                Parameters for parameterized queries. Can be a list for
                positional parameters (with ? placeholders) or a dict for
                named parameters. Values can be strings, numbers, booleans,
                or None. Note: tuples are also accepted at runtime but should
                be passed as lists for type compatibility.
                (default: :obj:`None`)

        Returns:
            Union[List[Dict[str, Any]], Dict[str, Any], str]:
                - For SELECT queries: List of dictionaries with column names as
                  keys and row values as values.
                - For write operations (INSERT, UPDATE, DELETE, CREATE, etc.):
                  A dictionary with 'status', 'message', and optionally
                  'rows_affected' keys.
                - For errors: An error message string starting with "Error:".
        """
        if not query or not query.strip():
            return "Error: Query cannot be empty"

        # Validate query mode (check for write operations in read-only mode)
        if self.read_only and self._is_write_query(query):
            return (
                "Error: Write operations are not allowed in read-only mode. "
                "The query contains write operations (INSERT, UPDATE, DELETE, "
                "DROP, CREATE, ALTER, TRUNCATE, etc.). Only SELECT queries "
                "are permitted."
            )

        try:
            logger.debug(f"Executing query: {query}...")

            cursor = self._connection.cursor()

            # Execute query with or without parameters
            if params is not None:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            # Check if this is a write operation first
            # DuckDB returns results for INSERT/UPDATE/DELETE (with count),
            # but we want to return empty list for write operations
            is_write = self._is_write_query(query)

            # Check if the query returned results by checking cursor.
            # description
            # This handles SELECT queries, CTEs (WITH ... SELECT ...),
            # EXPLAIN queries, SHOW queries, etc.
            if cursor.description is not None and not is_write:
                # Query returned results and it's not a write operation,
                # fetch them
                rows = cursor.fetchall()

                # Convert rows to dictionaries
                # SQLite with row_factory returns Row objects that can be
                # converted to dict
                # DuckDB returns tuples that need column names
                if (
                    self.database_type == "sqlite"
                    and rows
                    and hasattr(rows[0], "keys")
                ):
                    # SQLite Row objects can be converted directly to dict
                    results = [dict(row) for row in rows]
                else:
                    # DuckDB or other databases: use column names from
                    # description
                    columns = [desc[0] for desc in cursor.description]
                    results = [dict(zip(columns, row)) for row in rows]

                logger.debug(f"Query returned {len(results)} rows")
                return results
            else:
                # Query did not return results or is a write operation
                # (INSERT, UPDATE, DELETE, etc.)
                # Commit the transaction
                self._connection.commit()

                # Get affected rows count if available
                # Note: DuckDB doesn't support rowcount, SQLite does for DML
                rows_affected = getattr(cursor, "rowcount", -1)
                result_dict: Dict[str, Any] = {
                    "status": "success",
                }
                if rows_affected >= 0:
                    result_dict["rows_affected"] = rows_affected
                    result_dict["message"] = (
                        f"Query executed successfully. "
                        f"{rows_affected} row(s) affected."
                    )
                    logger.debug(
                        f"Write query executed successfully, "
                        f"{rows_affected} rows affected"
                    )
                else:
                    result_dict["message"] = "Query executed successfully."
                    logger.debug("Query executed successfully")
                return result_dict

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Query execution failed: {error_msg}")
            # Rollback on error
            try:
                self._connection.rollback()
            except Exception as rollback_error:
                logger.debug(f"Rollback failed: {rollback_error!s}")
            return f"Error: Query execution failed: {error_msg}"

    def list_tables(self) -> Union[List[str], str]:
        r"""List all tables in the database.

        This method queries the database to discover all available tables.
        It uses database-specific queries to retrieve table names.

        Returns:
            Union[List[str], str]: A list of table names in the database,
                or an error message string if the operation fails.
        """
        try:
            if self.database_type == "duckdb":
                # DuckDB uses SHOW TABLES
                result = self.execute_query("SHOW TABLES")
                # Check if result is an error message or unexpected dict
                if isinstance(result, str):
                    return result
                if isinstance(result, dict):
                    return (
                        f"Error: Unexpected result from SHOW TABLES: {result}"
                    )
                # Result format: [{'name': 'table1'}, {'name': 'table2'}]
                return [row["name"] for row in result]
            elif self.database_type == "sqlite":
                # SQLite uses sqlite_master system table
                result = self.execute_query(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )
                # Check if result is an error message or unexpected dict
                if isinstance(result, str):
                    return result
                if isinstance(result, dict):
                    return f"Error: Unexpected result from query: {result}"
                # Result format: [{'name': 'table1'}, {'name': 'table2'}]
                return [row["name"] for row in result]
            else:
                # For other databases, could use information_schema or similar
                return (
                    f"Error: list_tables not yet implemented for "
                    f"{self.database_type}"
                )
        except Exception as e:
            logger.error(f"Failed to list tables: {e!s}")
            return f"Error: Failed to list tables: {e!s}"

    def _get_table_schema(self, table_name: str) -> Union[Dict[str, Any], str]:
        r"""Internal helper method to get table schema information.

        Args:
            table_name (str): The name of the table to describe.

        Returns:
            Union[Dict[str, Any], str]: A dictionary containing 'columns',
                'primary_keys', and 'foreign_keys', or an error message string
                if the operation fails.
        """
        if not table_name or not table_name.strip():
            return "Error: Table name cannot be empty"

        try:
            if self.database_type == "duckdb":
                # Get column information using DESCRIBE
                # Safely quote the table name to prevent SQL injection
                quoted_table_name = self._quote_identifier(table_name)
                columns = self.execute_query(f"DESCRIBE {quoted_table_name}")

                # Check if result is an error message
                if isinstance(columns, str):
                    return columns
                # Also check if result is a status dict (not a list of columns)
                if isinstance(columns, dict):
                    return f"Error: Unexpected result from DESCRIBE: {columns}"

                # Extract primary keys
                primary_keys = [
                    col["column_name"]
                    for col in columns
                    if col.get("key") == "PRI"
                ]

                # Get foreign keys from information_schema
                # This query retrieves FK relationships by joining system
                # tables:
                # - table_constraints: finds FOREIGN KEY constraints
                # - referential_constraints: links FK to referenced constraint
                # - key_column_usage: gets column names (used twice for source/
                # target)
                foreign_keys = []
                try:
                    fk_query = """
                    SELECT
                        kcu.column_name,
                        kcu2.table_name AS references_table,
                        kcu2.column_name AS references_column
                    FROM information_schema.table_constraints AS tc
                    JOIN information_schema.referential_constraints AS rc
                        ON tc.constraint_name = rc.constraint_name
                    JOIN information_schema.key_column_usage AS kcu
                        ON tc.constraint_name = kcu.constraint_name
                    JOIN information_schema.table_constraints AS tc2
                        ON rc.unique_constraint_name = tc2.constraint_name
                    JOIN information_schema.key_column_usage AS kcu2
                        ON tc2.constraint_name = kcu2.constraint_name
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                        AND tc.table_name = ?
                    """
                    fk_results = self.execute_query(
                        fk_query, params=[table_name]
                    )
                    # Only process if result is a list of rows
                    if isinstance(fk_results, list):
                        foreign_keys = [
                            {
                                "column": fk["column_name"],
                                "references_table": fk["references_table"],
                                "references_column": fk["references_column"],
                            }
                            for fk in fk_results
                        ]
                except Exception as e:
                    # If foreign key query fails, log but don't fail
                    logger.debug(
                        f"Could not retrieve foreign keys "
                        f"for {table_name}: {e!s}"
                    )

                return {
                    "columns": columns,
                    "primary_keys": primary_keys,
                    "foreign_keys": foreign_keys,
                }
            elif self.database_type == "sqlite":
                # SQLite uses PRAGMA table_info for column information
                quoted_table_name = self._quote_identifier(table_name)
                pragma_result = self.execute_query(
                    f"PRAGMA table_info({quoted_table_name})"
                )

                # Check if result is an error message
                if isinstance(pragma_result, str):
                    return pragma_result
                # Also check if result is a status dict (not a list of rows)
                if isinstance(pragma_result, dict):
                    return (
                        f"Error: Unexpected result from "
                        f"PRAGMA: {pragma_result}"
                    )

                # Convert PRAGMA format to match DuckDB format
                sqlite_columns: List[Dict[str, Any]] = []
                sqlite_pks: List[str] = []
                for row in pragma_result:
                    is_primary_key = row["pk"] > 0
                    col_info: Dict[str, Any] = {
                        "column_name": row["name"],
                        "column_type": row["type"],
                        "null": "YES" if row["notnull"] == 0 else "NO",
                        "key": "PRI" if is_primary_key else None,
                        "default": row["dflt_value"],
                        "extra": None,
                    }
                    sqlite_columns.append(col_info)
                    if is_primary_key:
                        sqlite_pks.append(row["name"])

                # Get foreign keys using PRAGMA foreign_key_list (much
                # simpler!)
                sqlite_fks: List[Dict[str, Any]] = []
                try:
                    fk_result = self.execute_query(
                        f"PRAGMA foreign_key_list({quoted_table_name})"
                    )
                    # Only process if result is a list of rows
                    if isinstance(fk_result, list):
                        sqlite_fks = [
                            {
                                "column": fk["from"],
                                "references_table": fk["table"],
                                "references_column": fk["to"],
                            }
                            for fk in fk_result
                        ]
                except Exception as e:
                    # If foreign key query fails, log but don't fail
                    logger.debug(
                        f"Could not retrieve foreign keys for "
                        f"{table_name}: {e!s}"
                    )

                return {
                    "columns": sqlite_columns,
                    "primary_keys": sqlite_pks,
                    "foreign_keys": sqlite_fks,
                }
            else:
                # For other databases, could use information_schema or similar
                return (
                    f"Error: get_table_info not yet implemented for "
                    f"{self.database_type}"
                )
        except Exception as e:
            logger.error(f"Failed to get table schema for {table_name}: {e!s}")
            return f"Error: Failed to get table schema for {table_name}: {e!s}"

    def get_table_info(
        self, table_name: Optional[str] = None
    ) -> Union[Dict[str, Any], str]:
        r"""Get comprehensive information about table(s) in the database.

        This method provides a summary of table information including schema,
        primary keys, foreign keys, and row counts. If table_name is provided,
        returns info for that specific table. Otherwise, returns info for all
        tables.

        Args:
            table_name (Optional[str], optional): Name of a specific table to
                get info for. If None, returns info for all tables.
                (default: :obj:`None`)

        Returns:
            Union[Dict[str, Any], str]: A dictionary containing table
                information, or an error message string if the operation fails.
                If table_name is provided, returns info for that table with
                keys: 'table_name', 'columns', 'primary_keys', 'foreign_keys',
                'row_count'. Otherwise, returns a dictionary mapping table
                names to their info dictionaries.
        """
        # Validate table_name if provided
        if table_name is not None and (
            not table_name or not table_name.strip()
        ):
            return "Error: Table name cannot be empty"

        try:
            if table_name:
                # Get info for specific table
                schema_info = self._get_table_schema(table_name)
                # Check if result is an error message
                if isinstance(schema_info, str):
                    return schema_info

                # Get row count - safely quote table name to prevent SQL
                # injection
                quoted_table_name = self._quote_identifier(table_name)
                count_result = self.execute_query(
                    f"SELECT COUNT(*) as row_count FROM {quoted_table_name}"
                )
                # Check if result is an error message or not a list
                if isinstance(count_result, str):
                    return count_result
                if not isinstance(count_result, list):
                    return (
                        f"Error: Unexpected result from COUNT: {count_result}"
                    )
                row_count = count_result[0]["row_count"] if count_result else 0

                return {
                    "table_name": table_name,
                    "columns": schema_info["columns"],
                    "primary_keys": schema_info["primary_keys"],
                    "foreign_keys": schema_info["foreign_keys"],
                    "row_count": row_count,
                }
            else:
                # Get info for all tables
                tables = self.list_tables()
                # Check if result is an error message
                if isinstance(tables, str):
                    return tables

                result = {}
                for table in tables:
                    schema_info = self._get_table_schema(table)
                    # Check if result is an error message
                    if isinstance(schema_info, str):
                        return schema_info

                    # Safely quote table name to prevent SQL injection
                    quoted_table = self._quote_identifier(table)
                    count_result = self.execute_query(
                        f"SELECT COUNT(*) as row_count FROM {quoted_table}"
                    )
                    # Check if result is an error message or not a list
                    if isinstance(count_result, str):
                        return count_result
                    if not isinstance(count_result, list):
                        return (
                            f"Error: Unexpected result from COUNT: "
                            f"{count_result}"
                        )
                    row_count = (
                        count_result[0]["row_count"] if count_result else 0
                    )
                    result[table] = {
                        "table_name": table,
                        "columns": schema_info["columns"],
                        "primary_keys": schema_info["primary_keys"],
                        "foreign_keys": schema_info["foreign_keys"],
                        "row_count": row_count,
                    }
                return result
        except Exception as e:
            logger.error(f"Failed to get table info: {e!s}")
            return f"Error: Failed to get table info: {e!s}"

    def get_tools(self) -> List[FunctionTool]:
        r"""Get the list of available tools in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects representing the
                available functions in the toolkit.
        """
        return [
            FunctionTool(self.execute_query),
            FunctionTool(self.list_tables),
            FunctionTool(self.get_table_info),
        ]

    def __del__(self) -> None:
        r"""Clean up database connection on deletion."""
        if hasattr(self, "_connection") and self._connection:
            try:
                self._connection.close()
            except Exception as e:
                logger.debug(f"Error closing connection in __del__: {e}")
