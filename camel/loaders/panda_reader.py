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
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Union

import pandas as pd

if TYPE_CHECKING:
    from pandas import DataFrame
    from pandasai import SmartDataframe


def check_suffix(valid_suffixs: List[str]) -> Callable:
    r"""A decorator to check the file suffix of a given file path.

    Args:
        valid_suffix (str): The required file suffix.

    Returns:
        Callable: The decorator function.
    """

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(
            self, file_path: str, *args: Any, **kwargs: Dict[str, Any]
        ) -> "DataFrame":
            suffix = Path(file_path).suffix
            if suffix not in valid_suffixs:
                raise ValueError(
                    f"Only {', '.join(valid_suffixs)} files are supported"
                )
            return func(self, file_path, *args, **kwargs)

        return wrapper

    return decorator


class PandaReader:
    def __init__(self, config: Optional[Dict[str, Any]] = None, pure_pandas: bool = False) -> None:
        r"""Initializes the PandaReader class with support for LLM and pure Pandas modes.

        Args:
            config (Optional[Dict[str, Any]], optional): The configuration
                dictionary that can include LLM API settings for LLM-based
                processing. If not provided, it will use OpenAI with the API
                key from the OPENAI_API_KEY environment variable. You can
                customize the LLM configuration by providing a 'llm' key in
                the config dictionary. (default: :obj:`None`)
            use_pandas (bool, optional): If True, forces pure Pandas mode, disabling LLM usage.
                Defaults to False.
        """

        self.config = config or {}
        self.pure_pandas = pure_pandas
        self.df = None # The loaded DataFrame
        if self.pure_pandas and "llm" in self.config:
            raise ValueError("Cannot use LLM when pure_pandas is True")
        elif not self.pure_pandas and "llm" not in self.config:
            api_key = os.getenv("OPENAI_API_KEY")
            from pandasai.llm import OpenAI
            self.config["llm"] = OpenAI(api_token=api_key)

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
        self,
        data: Union["DataFrame", str],
        *args: Any,
        **kwargs: Dict[str, Any],
    ) -> Union["SmartDataframe", "DataFrame"]:
        r"""Loads data from a DataFrame or file into a SmartDataframe (LLM mode) or DataFrame (pure Pandas mode).
        args:
            data (Union[DataFrame, str]): The data to load.
            *args (Any): Additional positional arguments.
            **kwargs (Dict[str, Any]): Additional keyword arguments.

        Returns:
            SmartDataframe: The SmartDataframe object.
            DataFrame: if forced to use pure pandas
        """
        if isinstance(data, pd.DataFrame):
            self.df = data
        else:
            file_path = str(data)
            path = Path(file_path)
            if not file_path.startswith("http") and not path.exists():
                raise FileNotFoundError(f"File {file_path} not found")
            if path.suffix in self.__LOADER:
                self.df = self.__LOADER[path.suffix](file_path, *args, **kwargs)
            else:
                raise ValueError(f"Unsupported file format: {path.suffix}")

        if not self.pure_pandas and "llm" in self.config:
            from pandasai import SmartDataframe
            return SmartDataframe(self.df, config=self.config)
        return self.df

    def query(self, question: str) -> "DataFrame":
        r"""Executes a query on the loaded data using LLM or pure Pandas logic.

                Args:
                    question (str): Query string (e.g., "Which are the top 5 countries by sales?").

                Returns:
                    DataFrame: Query result as a pandas DataFrame.

                Raises:
                    ValueError: If no data is loaded, or if the query is unsupported in pure Pandas mode.
                """
        if self.df is None:
            raise ValueError("No data loaded. Call load() first.")

        if not self.pure_pandas and "llm" in self.config:
            return self.df.chat(question)

        # Pure Pandas mode
        question = question.lower().strip()
        ########################Each query type will need its own parsing
        if "top" in question and "sales" in question:
            try:
                k = int(question.split("top ")[1].split(" ")[0])
                if k <= 0:
                    raise ValueError("Number of top items must be positive")
                return self.df.sort_values(by="sales", ascending=False).head(k)
            except (IndexError, ValueError) as e:
                raise ValueError(f"Invalid top-k query: {question}. Use 'top N ...'.") from e
    @check_suffix([".csv"])
    def read_csv(
        self, file_path: str, *args: Any, **kwargs: Dict[str, Any]
    ) -> "DataFrame":
        r"""Reads a CSV file and returns a DataFrame.

        Args:
            file_path (str): The path to the CSV file.
            *args (Any): Additional positional arguments.
            **kwargs (Dict[str, Any]): Additional keyword arguments.

        Returns:
            DataFrame: The DataFrame object.
        """
        return pd.read_csv(file_path, *args, **kwargs)

    @check_suffix([".xlsx", ".xls"])
    def read_excel(
        self, file_path: str, *args: Any, **kwargs: Dict[str, Any]
    ) -> "DataFrame":
        r"""Reads an Excel file and returns a DataFrame.

        Args:
            file_path (str): The path to the Excel file.
            *args (Any): Additional positional arguments.
            **kwargs (Dict[str, Any]): Additional keyword arguments.

        Returns:
            DataFrame: The DataFrame object.
        """
        return pd.read_excel(file_path, *args, **kwargs)

    @check_suffix([".json"])
    def read_json(
        self, file_path: str, *args: Any, **kwargs: Dict[str, Any]
    ) -> "DataFrame":
        r"""Reads a JSON file and returns a DataFrame.

        Args:
            file_path (str): The path to the JSON file.
            *args (Any): Additional positional arguments.
            **kwargs (Dict[str, Any]): Additional keyword arguments.

        Returns:
            DataFrame: The DataFrame object.
        """
        return pd.read_json(file_path, *args, **kwargs)

    @check_suffix([".parquet"])
    def read_parquet(
        self, file_path: str, *args: Any, **kwargs: Dict[str, Any]
    ) -> "DataFrame":
        r"""Reads a Parquet file and returns a DataFrame.

        Args:
            file_path (str): The path to the Parquet file.
            *args (Any): Additional positional arguments.
            **kwargs (Dict[str, Any]): Additional keyword arguments.

        Returns:
            DataFrame: The DataFrame object.
        """
        return pd.read_parquet(file_path, *args, **kwargs)

    def read_sql(self, *args: Any, **kwargs: Dict[str, Any]) -> "DataFrame":
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
    ) -> "DataFrame":
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
    ) -> "DataFrame":
        r"""Reads a clipboard and returns a DataFrame.

        Args:
            *args (Any): Additional positional arguments.
            **kwargs (Dict[str, Any]): Additional keyword arguments.

        Returns:
            DataFrame: The DataFrame object.
        """
        return pd.read_clipboard(*args, **kwargs)

    @check_suffix([".html"])
    def read_html(
        self, file_path: str, *args: Any, **kwargs: Dict[str, Any]
    ) -> "DataFrame":
        r"""Reads an HTML file and returns a DataFrame.

        Args:
            file_path (str): The path to the HTML file.
            *args (Any): Additional positional arguments.
            **kwargs (Dict[str, Any]): Additional keyword arguments.

        Returns:
            DataFrame: The DataFrame object.
        """
        return pd.read_html(file_path, *args, **kwargs)

    @check_suffix([".feather"])
    def read_feather(
        self, file_path: str, *args: Any, **kwargs: Dict[str, Any]
    ) -> "DataFrame":
        r"""Reads a Feather file and returns a DataFrame.

        Args:
            file_path (str): The path to the Feather file.
            *args (Any): Additional positional arguments.
            **kwargs (Dict[str, Any]): Additional keyword arguments.

        Returns:
            DataFrame: The DataFrame object.
        """
        return pd.read_feather(file_path, *args, **kwargs)

    @check_suffix([".dta"])
    def read_stata(
        self, file_path: str, *args: Any, **kwargs: Dict[str, Any]
    ) -> "DataFrame":
        r"""Reads a Stata file and returns a DataFrame.

        Args:
            file_path (str): The path to the Stata file.
            *args (Any): Additional positional arguments.
            **kwargs (Dict[str, Any]): Additional keyword arguments.

        Returns:
            DataFrame: The DataFrame object.
        """
        return pd.read_stata(file_path, *args, **kwargs)

    @check_suffix([".sas"])
    def read_sas(
        self, file_path: str, *args: Any, **kwargs: Dict[str, Any]
    ) -> "DataFrame":
        r"""Reads a SAS file and returns a DataFrame.

        Args:
            file_path (str): The path to the SAS file.
            *args (Any): Additional positional arguments.
            **kwargs (Dict[str, Any]): Additional keyword arguments.

        Returns:
            DataFrame: The DataFrame object.
        """
        return pd.read_sas(file_path, *args, **kwargs)

    @check_suffix([".pkl"])
    def read_pickle(
        self, file_path: str, *args: Any, **kwargs: Dict[str, Any]
    ) -> "DataFrame":
        r"""Reads a Pickle file and returns a DataFrame.

        Args:
            file_path (str): The path to the Pickle file.
            *args (Any): Additional positional arguments.
            **kwargs (Dict[str, Any]): Additional keyword arguments.

        Returns:
            DataFrame: The DataFrame object.
        """
        return pd.read_pickle(file_path, *args, **kwargs)

    @check_suffix([".h5"])
    def read_hdf(
        self, file_path: str, *args: Any, **kwargs: Dict[str, Any]
    ) -> "DataFrame":
        r"""Reads an HDF file and returns a DataFrame.

        Args:
            file_path (str): The path to the HDF file.
            *args (Any): Additional positional arguments.
            **kwargs (Dict[str, Any]): Additional keyword arguments.

        Returns:
            DataFrame: The DataFrame object.
        """
        return pd.read_hdf(file_path, *args, **kwargs)

    @check_suffix([".orc"])
    def read_orc(
        self, file_path: str, *args: Any, **kwargs: Dict[str, Any]
    ) -> "DataFrame":
        r"""Reads an ORC file and returns a DataFrame.

        Args:
            file_path (str): The path to the ORC file.
            *args (Any): Additional positional arguments.
            **kwargs (Dict[str, Any]): Additional keyword arguments.

        Returns:
            DataFrame: The DataFrame object.
        """
        return pd.read_orc(file_path, *args, **kwargs)
