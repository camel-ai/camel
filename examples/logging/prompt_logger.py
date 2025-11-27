#!/usr/bin/env python3
"""
Simplified PromptLogger for CAMEL Terminal Bench

This module provides basic logging functionality for LLM prompts without
real-time HTML updates. Use llm_log_to_html.py to convert logs after execution.
"""

import json
import datetime
from pathlib import Path


class PromptLogger:
    r"""Logger to capture all prompts sent to the LLM.

    This class provides a simple way to log all LLM interactions to a file
    during Terminal Bench task execution. The log file can later be converted
    to an interactive HTML viewer using the llm_log_to_html.py tool.

    Args:
        log_file_path (str): Path to the log file where prompts will be saved.

    Attributes:
        log_file_path (str): Path to the log file.
        prompt_counter (int): Counter for tracking the number of prompts logged.

    Example:
        >>> logger = PromptLogger("/path/to/llm_prompts.log")
        >>> logger.log_prompt(messages, model_info="gpt-4")
        >>> # Later convert to HTML:
        >>> # python llm_log_to_html.py /path/to/llm_prompts.log
    """

    def __init__(self, log_file_path):
        self.log_file_path = log_file_path
        self.prompt_counter = 0

        # Ensure parent directory exists
        Path(log_file_path).parent.mkdir(parents=True, exist_ok=True)

    def log_prompt(self, openai_messages, model_info="", iteration=0):
        r"""Log the prompt messages to file.

        This method appends a formatted prompt entry to the log file, including
        the messages, timestamp, and metadata.

        Args:
            openai_messages (list): List of message dictionaries in OpenAI format.
                Each message should have 'role' and 'content' fields.
            model_info (str, optional): Information about the model being used
                (e.g., "gpt-4", "gpt-3.5-turbo"). (default: :obj:`""`)
            iteration (int, optional): The iteration number in multi-turn
                conversations. (default: :obj:`0`)

        Returns:
            int: The prompt counter value for this log entry.

        Example:
            >>> messages = [
            ...     {"role": "system", "content": "You are a helpful assistant."},
            ...     {"role": "user", "content": "Hello!"}
            ... ]
            >>> logger.log_prompt(messages, model_info="gpt-4", iteration=1)
            1
        """
        self.prompt_counter += 1
        timestamp = datetime.datetime.now().isoformat()

        # Write to .log file
        with open(self.log_file_path, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"PROMPT #{self.prompt_counter} - {model_info} "
                   f"(iteration {iteration})\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"{'='*80}\n")
            f.write(json.dumps(openai_messages, indent=2, ensure_ascii=False))
            f.write(f"\n{'='*80}\n\n")

        return self.prompt_counter

    def get_stats(self):
        r"""Get statistics about the logged prompts.

        Returns:
            dict: Dictionary containing logging statistics with keys:
                - 'total_prompts' (int): Total number of prompts logged
                - 'log_file' (str): Path to the log file
                - 'file_exists' (bool): Whether the log file exists
        """
        return {
            'total_prompts': self.prompt_counter,
            'log_file': self.log_file_path,
            'file_exists': Path(self.log_file_path).exists()
        }
