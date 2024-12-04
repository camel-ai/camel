from typing import List
from .filter_function import FilterFunction

class InstructionFilter:
    def __init__(self):
        self.filter_functions: List[FilterFunction] = []

    def add_filter(self, filter_function: FilterFunction):
        """Add a custom filter function to be used in filtering."""
        self.filter_functions.append(filter_function)

    def filter(self, instruction: str) -> bool:
        """
        Check if the given instruction passes all filter functions.

        Args:
        instruction (str): The instruction to evaluate.

        Returns:
        bool: True if the instruction passes all filters, False otherwise.
        """
        return all(f.apply(instruction) for f in self.filter_functions)
