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
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

import pandas as pd  # type: ignore[import-untyped]
from pandas import DataFrame
from pandasai import SmartDataframe  # type: ignore[import-untyped]
from pandasai.llm import OpenAI  # type: ignore[import-untyped]


class PandaReader:
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        r"""Initializes the PandaReader class.

        Args:
            config (Optional[Dict[str, Any]], optional):
                The configuration dictionary. (default: :obj:`None`)
        """

        self.config = config or {}
        if "llm" not in self.config:
            self.config["llm"] = OpenAI(
                api_token=os.getenv("OPENAI_API_KEY"),
            )

        self.__LOADER = {
            ".csv": self.read_csv,
            ".xlsx": self.read_excel,
            ".xls": self.read_excel,
            ".json": self.read_json,
            ".parquet": self.read_parquet,
            ".sql": self.read_sql,
            ".html": self.read_html,
            ".feather": self.read_feather,
            ".dta": self.read_stata,
            ".sas": self.read_sas,
            ".pkl": self.read_pickle,
            ".h5": self.read_hdf,
            ".orc": self.read_orc,
        }

    def load(
        self, data: Union[DataFrame, str], *args: Any, **kwargs: Dict[str, Any]
    ) -> SmartDataframe:
        r"""Loads a file or DataFrame and returns a SmartDataframe object.

        args:
            data (Union[DataFrame, str]): The data to load.
            *args (Any): Additional positional arguments.
            **kwargs (Dict[str, Any]): Additional keyword arguments.

        Returns:
            SmartDataframe: The SmartDataframe object.
        """
        if isinstance(data, DataFrame):
            return SmartDataframe(data, config=self.config)
        file_path = str(data)
        path = Path(file_path)
        if not file_path.startswith("http") and not path.exists():
            raise FileNotFoundError(f"File {file_path} not found")
        if path.suffix in self.__LOADER:
            return SmartDataframe(
                self.__LOADER[path.suffix](file_path, *args, **kwargs),  # type: ignore[operator]
                config=self.config,
            )
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")

    def read_csv(
        self, file_path: str, *args: Any, **kwargs: Dict[str, Any]
    ) -> DataFrame:
        r"""Reads a CSV file and returns a DataFrame.

        Args:
            file_path (str): The path to the CSV file.
            *args (Any): Additional positional arguments.
            **kwargs (Dict[str, Any]): Additional keyword arguments.

        Returns:
            DataFrame: The DataFrame object.
        """
        if not file_path.endswith(".csv"):
            raise ValueError("Only CSV files are supported")
        return pd.read_csv(file_path, *args, **kwargs)

    def read_excel(
        self, file_path: str, *args: Any, **kwargs: Dict[str, Any]
    ) -> DataFrame:
        r"""Reads an Excel file and returns a DataFrame.

        Args:
            file_path (str): The path to the Excel file.
            *args (Any): Additional positional arguments.
            **kwargs (Dict[str, Any]): Additional keyword arguments.

        Returns:
            DataFrame: The DataFrame object.
        """
        if not file_path.endswith(".xlsx") and not file_path.endswith(".xls"):
            raise ValueError("Only Excel files are supported")
        return pd.read_excel(file_path, *args, **kwargs)

    def read_json(
        self, file_path: str, *args: Any, **kwargs: Dict[str, Any]
    ) -> DataFrame:
        r"""Reads a JSON file and returns a DataFrame.

        Args:
            file_path (str): The path to the JSON file.
            *args (Any): Additional positional arguments.
            **kwargs (Dict[str, Any]): Additional keyword arguments.

        Returns:
            DataFrame: The DataFrame object.
        """
        if not file_path.endswith(".json"):
            raise ValueError("Only JSON files are supported")
        return pd.read_json(file_path, *args, **kwargs)

    def read_parquet(
        self, file_path: str, *args: Any, **kwargs: Dict[str, Any]
    ) -> DataFrame:
        r"""Reads a Parquet file and returns a DataFrame.

        Args:
            file_path (str): The path to the Parquet file.
            *args (Any): Additional positional arguments.
            **kwargs (Dict[str, Any]): Additional keyword arguments.

        Returns:
            DataFrame: The DataFrame object.
        """
        if not file_path.endswith(".parquet"):
            raise ValueError("Only Parquet files are supported")
        return pd.read_parquet(file_path, *args, **kwargs)

    def read_sql(self, *args: Any, **kwargs: Dict[str, Any]) -> DataFrame:
        r"""Reads a SQL file and returns a DataFrame.

        Args:
            *args (Any): Additional positional arguments.
            **kwargs (Dict[str, Any]): Additional keyword arguments.

        Returns:
            DataFrame: The DataFrame object.
        """
        return pd.read_sql(*args, **kwargs)

    def read_table(
        self, file_path: str, *args: Any, **kwargs: Dict[str, Any]
    ) -> DataFrame:
        r"""Reads a table and returns a DataFrame.

        Args:
            file_path (str): The path to the table.
            *args (Any): Additional positional arguments.
            **kwargs (Dict[str, Any]): Additional keyword arguments.

        Returns:
            DataFrame: The DataFrame object.
        """
        return pd.read_table(file_path, *args, **kwargs)

    def read_clipboard(
        self, *args: Any, **kwargs: Dict[str, Any]
    ) -> DataFrame:
        r"""Reads a clipboard and returns a DataFrame.

        Args:
            *args (Any): Additional positional arguments.
            **kwargs (Dict[str, Any]): Additional keyword arguments.

        Returns:
            DataFrame: The DataFrame object.
        """
        return pd.read_clipboard(*args, **kwargs)

    def read_html(
        self, file_path: str, *args: Any, **kwargs: Dict[str, Any]
    ) -> DataFrame:
        r"""Reads an HTML file and returns a DataFrame.

        Args:
            file_path (str): The path to the HTML file.
            *args (Any): Additional positional arguments.
            **kwargs (Dict[str, Any]): Additional keyword arguments.

        Returns:
            DataFrame: The DataFrame object.
        """
        if not file_path.endswith(".html"):
            raise ValueError("Only HTML files are supported")
        return pd.read_html(file_path, *args, **kwargs)

    def read_feather(
        self, file_path: str, *args: Any, **kwargs: Dict[str, Any]
    ) -> DataFrame:
        r"""Reads a Feather file and returns a DataFrame.

        Args:
            file_path (str): The path to the Feather file.
            *args (Any): Additional positional arguments.
            **kwargs (Dict[str, Any]): Additional keyword arguments.

        Returns:
            DataFrame: The DataFrame object.
        """
        if not file_path.endswith(".feather"):
            raise ValueError("Only Feather files are supported")
        return pd.read_feather(file_path, *args, **kwargs)

    def read_stata(
        self, file_path: str, *args: Any, **kwargs: Dict[str, Any]
    ) -> DataFrame:
        r"""Reads a Stata file and returns a DataFrame.

        Args:
            file_path (str): The path to the Stata file.
            *args (Any): Additional positional arguments.
            **kwargs (Dict[str, Any]): Additional keyword arguments.

        Returns:
            DataFrame: The DataFrame object.
        """
        if not file_path.endswith(".dta"):
            raise ValueError("Only Stata files are supported")
        return pd.read_stata(file_path, *args, **kwargs)

    def read_sas(
        self, file_path: str, *args: Any, **kwargs: Dict[str, Any]
    ) -> DataFrame:
        r"""Reads a SAS file and returns a DataFrame.

        Args:
            file_path (str): The path to the SAS file.
            *args (Any): Additional positional arguments.
            **kwargs (Dict[str, Any]): Additional keyword arguments.

        Returns:
            DataFrame: The DataFrame object.
        """
        if not file_path.endswith(".sas"):
            raise ValueError("Only SAS files are supported")
        return pd.read_sas(file_path, *args, **kwargs)

    def read_pickle(
        self, file_path: str, *args: Any, **kwargs: Dict[str, Any]
    ) -> DataFrame:
        r"""Reads a Pickle file and returns a DataFrame.

        Args:
            file_path (str): The path to the Pickle file.
            *args (Any): Additional positional arguments.
            **kwargs (Dict[str, Any]): Additional keyword arguments.

        Returns:
            DataFrame: The DataFrame object.
        """
        if not file_path.endswith(".pkl"):
            raise ValueError("Only Pickle files are supported")
        return pd.read_pickle(file_path, *args, **kwargs)

    def read_hdf(
        self, file_path: str, *args: Any, **kwargs: Dict[str, Any]
    ) -> DataFrame:
        r"""Reads an HDF file and returns a DataFrame.

        Args:
            file_path (str): The path to the HDF file.
            *args (Any): Additional positional arguments.
            **kwargs (Dict[str, Any]): Additional keyword arguments.

        Returns:
            DataFrame: The DataFrame object.
        """
        if not file_path.endswith(".h5"):
            raise ValueError("Only HDF files are supported")
        return pd.read_hdf(file_path, *args, **kwargs)

    def read_orc(
        self, file_path: str, *args: Any, **kwargs: Dict[str, Any]
    ) -> DataFrame:
        r"""Reads an ORC file and returns a DataFrame.

        Args:
            file_path (str): The path to the ORC file.
            *args (Any): Additional positional arguments.
            **kwargs (Dict[str, Any]): Additional keyword arguments.

        Returns:
            DataFrame: The DataFrame object.
        """
        if not file_path.endswith(".orc"):
            raise ValueError("Only ORC files are supported")
        return pd.read_orc(file_path, *args, **kwargs)
