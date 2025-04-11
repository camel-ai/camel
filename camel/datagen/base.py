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

import json
import os
from typing import Any, Dict, List, Optional, Union

from camel.logger import get_logger

logger = get_logger(__name__)


class BaseDataGenPipeline:
    r"""Base class for all data generation pipelines.
    
    Provides a unified interface for data generation pipelines,
    allowing for flexible input and output options. It includes methods for loading 
    data from different sources and saving results to files.
    
    Subclasses should implement the `generate` method to define their specific
    data generation workflow.
    
    Attributes:
        output_path (Optional[str]): Path to save generated data.
    """
    
    def __init__(self, output_path: Optional[str] = None):
        r"""Initialize the base data generation pipeline.
        
        Args:
            output_path (Optional[str]): Path to save generated data.
                If None, results will only be returned without saving to file.
                (default: :obj:`None`)
        """
        self.output_path = output_path
    
    def load_data_from_file(self, file_path: str) -> List[Dict[str, Any]]:
        r"""Load data from a JSONL file.
        
        Args:
            file_path (str): Path to the JSONL file.
            
        Returns:
            List[Dict[str, Any]]: List of data entries.
            
        Raises:
            FileNotFoundError: If the file does not exist.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        data = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    data.append(json.loads(line))
        return data
    
    def load_data_from_jsonl_str(self, jsonl_str: str) -> List[Dict[str, Any]]:
        r"""Load data from a JSONL string.
        
        Args:
            jsonl_str (str): JSONL formatted string.
            
        Returns:
            List[Dict[str, Any]]: List of data entries.
        """
        data = []
        for line in jsonl_str.splitlines():
            line = line.strip()
            if line:
                data.append(json.loads(line))
        return data
    
    def load_data(
        self, data: Union[str, List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        r"""Unified method for loading data from various formats.
        
        This method accepts:
        - File path to a JSONL file
        - JSONL string
        - List of dictionaries
        
        Args:
            data (Union[str, List[Dict[str, Any]]]): Data input which can be
                either a file path, JSONL string, or list of dictionaries.
                
        Returns:
            List[Dict[str, Any]]: Loaded data as list of dictionaries.
            
        Raises:
            ValueError: If the data format is invalid or unsupported.
        """
        if isinstance(data, list):
            return data
        
        if not isinstance(data, str):
            raise ValueError(
                "Data must be either a file path, JSONL string, "
                "or list of dictionaries"
            )
        
        # Check if it's a file path
        if os.path.exists(data):
            return self.load_data_from_file(data)
        
        # Try to parse as JSONL string
        try:
            return self.load_data_from_jsonl_str(data)
        except json.JSONDecodeError:
            raise ValueError(
                "Data string could not be parsed as JSONL. "
                "Ensure it's a valid JSONL format."
            )
    
    def save_results(
        self, 
        results: List[Dict[str, Any]], 
        output_path: Optional[str] = None
    ) -> None:
        r"""Save results to a JSON file.
        
        Args:
            results (List[Dict[str, Any]]): Results to save.
            output_path (Optional[str]): Path to save results.
                If None, uses the pipeline's output_path.
                (default: :obj:`None`)
                
        Raises:
            ValueError: If no output path is provided.
        """
        path = output_path or self.output_path
        if not path:
            raise ValueError(
                "No output path provided. Either set output_path during "
                "initialization or provide it to save_results."
            )
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({"results": results}, f, indent=2, ensure_ascii=False)
        logger.info(f"Results saved to {path}")
    
    def save_jsonl(
        self, 
        results: List[Dict[str, Any]], 
        output_path: Optional[str] = None
    ) -> None:
        r"""Save results to a JSONL file.
        
        Args:
            results (List[Dict[str, Any]]): Results to save.
            output_path (Optional[str]): Path to save results.
                If None, uses the pipeline's output_path.
                (default: :obj:`None`)
                
        Raises:
            ValueError: If no output path is provided.
        """
        path = output_path or self.output_path
        if not path:
            raise ValueError(
                "No output path provided. Either set output_path during "
                "initialization or provide it to save_jsonl."
            )
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            for item in results:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        logger.info(f"Results saved to {path}")
    
    def safe_write_jsonl(
        self, 
        results: List[Dict[str, Any]], 
        output_path: Optional[str] = None
    ) -> None:
        r"""Safely write results to a JSONL file using atomic operations.
        
        Args:
            results (List[Dict[str, Any]]): Results to save.
            output_path (Optional[str]): Path to save results.
                If None, uses the pipeline's output_path.
                (default: :obj:`None`)
                
        Raises:
            ValueError: If no output path is provided.
        """
        path = output_path or self.output_path
        if not path:
            raise ValueError(
                "No output path provided. Either set output_path during "
                "initialization or provide it to safe_write_jsonl."
            )
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        
        # Write to temporary file first
        temp_path = path + ".tmp"
        with open(temp_path, 'w', encoding='utf-8') as f:
            for item in results:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
                
        # Replace the original file
        os.replace(temp_path, path)
        logger.info(f"Results safely saved to {path}")
    
    def generate(self, *args, **kwargs) -> List[Dict[str, Any]]:
        r"""Generate data based on the pipeline's implementation.
        
        Subclasses should implement this method to define their specific
        data generation logic.
        
        Returns:
            List[Dict[str, Any]]: Generated data.
        """
        raise NotImplementedError(
            "Subclasses must implement the generate method"
        ) 