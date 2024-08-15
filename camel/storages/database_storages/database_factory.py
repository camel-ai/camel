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

from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import ArgumentError, DBAPIError, OperationalError

from camel.storages.database_storages.database_manager import DatabaseManager
from camel.storages.database_storages.postgresql_manager import (
    PostgreSQLManager,
)


# Database factory
class DatabaseFactory:
    r"""A factory class for creating instances of database managers."""

    @staticmethod
    def get_database_manager(conn_string: str) -> DatabaseManager:
        r"""Creates and returns a database manager based on the 
        connection string.

        This method parses the connection string to determine the
        type of database being used. If the database type is not
        PostgreSQL, a ValueError is raised. If the connection cannot
        be established, the exception is caught and returned as a string.

        Args:
            conn_string (str): The connection string used to connect to the
            database.(for now, only support postgresql database.)

        Returns:
            DatabaseManager: An instance of the appropriate database manager.
            If an Error occurs, the error message is returned as a string.
        """
        try:
            # conn_string format follow this: postgresql://
            # user:password@localhost/dbname
            url = make_url(conn_string)
            db_type = url.get_backend_name()

            if db_type != 'postgresql':
                raise ValueError(f"Unsupported database type: {db_type}")

            engine = create_engine(conn_string)
            connection = engine.connect()
            connection.close()
            db_manager = PostgreSQLManager(conn_string)
            return db_manager

        except ArgumentError as e:
            raise ValueError(
                f"Invalid connection string: {conn_string}. Please ensure it ",
                "is in the correct format. ",
                "Example: 'postgresql://user:password@localhost/dbname'",
            ) from e
        except (OperationalError, DBAPIError) as e:
            raise ConnectionError(
                "Failed to connect to the database using the provided ",
                f"connection string: {conn_string}. ",
                "Please check your network connection, database server ",
                "status, and credentials.",
            ) from e
