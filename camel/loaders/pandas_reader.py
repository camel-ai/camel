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
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Union

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


class PandasReader:
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        r"""Initializes the PandasReader class.

        Args:
            config (Optional[Dict[str, Any]], optional): The configuration
                dictionary that can include LLM API settings for LLM-based
                processing. If not provided, no LLM will be configured by
                default. You can customize the LLM configuration by providing
                a 'llm' key in the config dictionary. (default: :obj:`None`)
        """
        self.config = config or {}

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
    ) -> Union["DataFrame", "SmartDataframe"]:
        r"""Loads a file or DataFrame and returns a DataFrame or
        SmartDataframe object.

        If an LLM is configured in the config dictionary, a SmartDataframe
        will be returned, otherwise a regular pandas DataFrame will be
        returned.

        args:
            data (Union[DataFrame, str]): The data to load.
            *args (Any): Additional positional arguments.
            **kwargs (Dict[str, Any]): Additional keyword arguments.

        Returns:
            Union[DataFrame, SmartDataframe]: The DataFrame or SmartDataframe
                object.
        """
        from pandas import DataFrame

        # Load the data into a pandas DataFrame
        if isinstance(data, DataFrame):
            df = data
        else:
            file_path = str(data)
            path = Path(file_path)
            if not file_path.startswith("http") and not path.exists():
                raise FileNotFoundError(f"File {file_path} not found")
            if path.suffix in self.__LOADER:
                df = self.__LOADER[path.suffix](file_path, *args, **kwargs)  # type: ignore[operator]
            else:
                raise ValueError(f"Unsupported file format: {path.suffix}")

        # If an LLM is configured, return a SmartDataframe, otherwise return a
        # regular DataFrame
        if "llm" in self.config:
            from pandasai import SmartDataframe

            return SmartDataframe(df, config=self.config)
        else:
            return df

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
        import pandas as pd

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
        import pandas as pd

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
        import pandas as pd

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
        import pandas as pd

        return pd.read_parquet(file_path, *args, **kwargs)

    def read_sql(self, *args: Any, **kwargs: Dict[str, Any]) -> "DataFrame":
        r"""Reads a SQL file and returns a DataFrame.

        Args:
            *args (Any): Additional positional arguments.
            **kwargs (Dict[str, Any]): Additional keyword arguments.

        Returns:
            DataFrame: The DataFrame object.
        """
        import pandas as pd

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
        import pandas as pd

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
        import pandas as pd

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
        import pandas as pd

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
        import pandas as pd

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
        import pandas as pd

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
        import pandas as pd

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
        import pandas as pd

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
        import pandas as pd

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
        import pandas as pd

        return pd.read_orc(file_path, *args, **kwargs)
