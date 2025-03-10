# memory_toolkit.py
import json
from typing import Optional

from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.memories import ChatHistoryMemory, MemoryRecord, ScoreBasedContextCreator

class MemoryToolkit(BaseToolkit):
    r"""
    A toolkit that provides methods for saving, loading, and clearing a ChatAgent's memory.
    These methods are exposed as FunctionTool objects for function calling.
    Internally, it calls:
      - agent.save_memory(path)
      - agent.load_memory(new_memory_obj)
      - agent.load_memory_from_path(path)
      - agent.clear_memory()
    """
    
    def __init__(self, agent: 'ChatAgent', timeout: Optional[float] = None):
        super().__init__(timeout=timeout)
        self.agent = agent

    def save(self, path: str) -> str:
        r"""
        Saves the agent's current memory to a JSON file by calling agent.save_memory(path).
        
        Args:
            path (str): The file path to save the memory to.
        
        Returns:
            str: Confirmation message.
        """
        self.agent.save_memory(path)
        return f"Memory saved to {path}"

    def load(self, memory_json: str) -> str:
        r"""
        Loads memory into the agent from a JSON string:
          1) Parse `memory_json` as a list of memory records
          2) Create a fresh ChatHistoryMemory
          3) Write records into that memory
          4) Call agent.load_memory(...) with that new memory
        
        Args:
            memory_json (str): A JSON string containing memory records.
        
        Returns:
            str: Confirmation or error message.
        """
        try:
            data = json.loads(memory_json.strip())
            if not isinstance(data, list):
                return "[ERROR] Memory data should be a list of records."

            # Build a fresh ChatHistoryMemory
            context_creator = ScoreBasedContextCreator(
                token_counter=self.agent.model_backend.token_counter,
                token_limit=self.agent.model_backend.token_limit,
            )
            new_memory = ChatHistoryMemory(context_creator)

            # Convert each record dict -> MemoryRecord
            for record_dict in data:
                record = MemoryRecord.from_dict(record_dict)
                new_memory.write_record(record)

            # Load into the agent
            self.agent.load_memory(new_memory)
            return "Loaded memory from provided JSON string."
        except json.JSONDecodeError:
            return "[ERROR] Invalid JSON string provided."
        except Exception as e:
            return f"[ERROR] Failed to load memory: {str(e)}"

    def load_from_path(self, path: str) -> str:
        r"""
        Loads the agent's memory from a JSON file by calling agent.load_memory_from_path(path).
        
        Args:
            path (str): The file path to load the memory from.
        
        Returns:
            str: Confirmation message.
        """
        self.agent.load_memory_from_path(path)
        return f"Memory loaded from {path}"

    def clear_memory(self) -> str:
        r"""
        Clears the agent's memory by calling agent.clear_memory().
        
        Returns:
            str: Confirmation message.
        """
        self.agent.clear_memory()
        return "Memory has been cleared."

    def get_tools(self) -> list[FunctionTool]:
        r"""
        Expose the memory management methods as function tools for the ChatAgent.
        
        Returns:
            list[FunctionTool]: List of FunctionTool objects.
        """
        return [
            FunctionTool(self.save),
            FunctionTool(self.load),
            FunctionTool(self.load_from_path),
            FunctionTool(self.clear_memory),
        ]