from pathlib import Path
from typing import Any, Dict, Optional, Union
import pandas as pd
from pandas import DataFrame
import os
from pandasai.llm import OpenAI
from pandasai import SmartDataframe

class PandaReader:

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}
        if not "llm" in self.config:
            self.config["llm"] = OpenAI(
                api_token=os.getenv("OPENAI_API_KEY"),
            )
    
    def load(self, data: Union[DataFrame, str], *args: Any, **kwargs: Dict[str, Any]) -> SmartDataframe:
        if isinstance(data, DataFrame):
            return SmartDataframe(data, config=self.config)
        file_path = str(data)
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File {file_path} not found")
        if path.suffix == ".csv":
            return SmartDataframe(self.read_csv(file_path, *args, **kwargs), config=self.config)
        elif path.suffix == ".xlsx" or path.suffix == ".xls":
            return SmartDataframe(self.read_excel(file_path, *args, **kwargs), config=self.config)
        elif path.suffix == ".json":
            return SmartDataframe(self.read_json(file_path, *args, **kwargs), config=self.config)
        elif path.suffix == ".parquet":
            return SmartDataframe(self.read_parquet(file_path, *args, **kwargs), config=self.config)
        elif path.suffix == ".sql":
            return SmartDataframe(self.read_sql(file_path, *args, **kwargs), config=self.config)
        elif path.suffix == ".html":
            return SmartDataframe(self.read_html(file_path, *args, **kwargs), config=self.config)
        elif path.suffix == ".feather":
            return SmartDataframe(self.read_feather(file_path, *args, **kwargs), config=self.config)
        elif path.suffix == ".dta":
            return SmartDataframe(self.read_stata(file_path, *args, **kwargs), config=self.config)
        elif path.suffix == ".sas":
            return SmartDataframe(self.read_sas(file_path, *args, **kwargs), config=self.config)
        elif path.suffix == ".pkl":
            return SmartDataframe(self.read_pickle(file_path, *args, **kwargs), config=self.config)
        elif path.suffix == ".h5":
            return SmartDataframe(self.read_hdf(file_path, *args, **kwargs), config=self.config)
        elif path.suffix == ".orc":
            return SmartDataframe(self.read_orc(file_path, *args, **kwargs), config=self.config)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")

    def read_csv(self, file_path: str, *args: Any, **kwargs: Dict[str, Any]) -> DataFrame:
        r"""Reads a CSV file and returns a DataFrame.
        
        Args:
            file_path (str): The path to the CSV file.
            *args (Any): Additional positional arguments.
            **kwargs (Dict[str, Any]): Additional keyword arguments.            
            
        Returns:
            DataFrame: The DataFrame object.
        """
        if not file_path.endswith('.csv'):
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
        if not file_path.endswith('.xlsx'):
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
        if not file_path.endswith('.json'):
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
        if not file_path.endswith('.parquet'):
            raise ValueError("Only Parquet files are supported")
        return pd.read_parquet(file_path, *args, **kwargs)
    
    def read_sql(
        self, file_path: str, *args: Any, **kwargs: Dict[str, Any]
    ) -> DataFrame:
        r"""Reads a SQL file and returns a DataFrame.
        
        Args:
            file_path (str): The path to the SQL file.
            *args (Any): Additional positional arguments.
            **kwargs (Dict[str, Any]): Additional keyword arguments.
            
        Returns:
            DataFrame: The DataFrame object.
        """
        if not file_path.endswith('.sql'):
            raise ValueError("Only SQL files are supported")
        return pd.read_sql(file_path, *args, **kwargs)
    
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
        if not file_path.endswith('.html'):
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
        if not file_path.endswith('.feather'):
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
        if not file_path.endswith('.dta'):
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
        if not file_path.endswith('.sas'):
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
        if not file_path.endswith('.pkl'):
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
        if not file_path.endswith('.h5'):
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
        if not file_path.endswith('.orc'):
            raise ValueError("Only ORC files are supported")
        return pd.read_orc(file_path, *args, **kwargs)
    
    def read_html(
        self, file_path: str, *args: Any, **kwargs: Dict[str, Any]
    ) -> DataFrame:
        r"""Reads a HTML file and returns a DataFrame.
        
        Args:
            file_path (str): The path to the HTML file.
            *args (Any): Additional positional arguments.
            **kwargs (Dict[str, Any]): Additional keyword arguments.
            
        Returns:
            DataFrame: The DataFrame object.
        """
        if not file_path.endswith('.html'):
            raise ValueError("Only HTML files are supported")
        return pd.read_html(file_path, *args, **kwargs)
