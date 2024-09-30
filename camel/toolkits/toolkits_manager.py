import difflib
import importlib
import inspect
import pkgutil
from typing import Callable, List, Optional

from camel.toolkits.openai_function import OpenAIFunction


class ToolManager:
    r"""
    A class representing a manager for dynamically loading and accessing
    toolkits.

    The ToolManager loads all callable toolkits from the `camel.toolkits`
    package and provides methods to list, retrieve, and search them as
    OpenAIFunction objects.
    """

    def __init__(self):
        r"""
        Initializes the ToolManager and loads all available toolkits.
        """
        self.toolkits = {}
        self._load_toolkits()

    def _load_toolkits(self):
        r"""
        Dynamically loads all toolkits from the `camel.toolkits` package.

        It iterates through all modules in the package, checking for the
        presence of an `__all__` attribute to explicitly control what
        functions to export.
        If `__all__` is not present, it ignores any function starting with `_`.
        """
        package = importlib.import_module('camel.toolkits')
        for _, module_name, _ in pkgutil.iter_modules(package.__path__):
            module = importlib.import_module(f'camel.toolkits.{module_name}')

            if hasattr(module, '__all__'):
                for name in module.__all__:
                    func = getattr(module, name, None)
                    if callable(func) and func.__module__ == module.__name__:
                        self.toolkits[name] = func
            else:
                for name, func in inspect.getmembers(
                    module, inspect.isfunction
                ):
                    if (
                        not name.startswith('_')
                        and func.__module__ == module.__name__
                    ):
                        self.toolkits[name] = func

    def _load_toolkit_class(self):
        r"""
        todo:Dynamically loads all toolkits class for user to define their own
        toolkit by setting the keys or other conifgs.
        """
        pass

    def add_toolkit(self, tookit: Callable):
        r"""
        todo: let user add toolkit to the toolkits list
        """
        pass

    def list_toolkits(self):
        r"""
        Lists the names of all available toolkits.

        Returns:
            List[str]: A list of all toolkit function names available for use.
        """
        return list(self.toolkits.keys())

    def get_toolkit(self, name: str) -> OpenAIFunction | str:
        r"""
        Retrieves the specified toolkit as an OpenAIFunction object.

        Args:
            name (str): The name of the toolkit function to retrieve.

        Returns:
            OpenAIFunction: The toolkit wrapped as an OpenAIFunction.

        Raises:
            ValueError: If the specified toolkit is not found.
        """
        toolkit = self.toolkits.get(name)
        if toolkit:
            return OpenAIFunction(toolkit)
        return f"Toolkit '{name}' not found."

    def get_toolkits(self, names: list[str]) -> list[OpenAIFunction] | str:
        r"""
        Retrieves the specified toolkit as an OpenAIFunction object.

        Args:
            name (str): The name of the toolkit function to retrieve.

        Returns:
            OpenAIFunctions (list): The toolkits wrapped as an OpenAIFunction.

        Raises:
            ValueError: If the specified toolkit is not found.
        """
        toolkits: list[OpenAIFunction] = []
        for name in names:
            current_toolkit = self.toolkits.get(name)
            if current_toolkit:
                toolkits.append(OpenAIFunction(current_toolkit))
        if len(toolkits) > 0:
            return toolkits
        return f"Toolkit '{name}' not found."

    def _default_search_algorithm(
        self, keyword: str, description: str
    ) -> bool:
        r"""
        Default search algorithm using fuzzy matching.

        Args:
            keyword (str): The keyword to search for.
            description (str): The description to search within.

        Returns:
            bool: True if a match is found based on similarity, False
            otherwise.
        """
        ratio = difflib.SequenceMatcher(
            None, keyword.lower(), description.lower()
        ).ratio()
        return (
            ratio > 0.6
        )  # A threshold of 0.6 for fuzzy matching (adjustable)

    def search_toolkits(
        self,
        keyword: str,
        algorithm: Optional[Callable[[str, str], bool]] = None,
    ) -> List[str]:
        r"""
        Searches for toolkits based on a keyword in their descriptions using
        the provided search algorithm.

        Args:
            keyword (str): The keyword to search for in toolkit descriptions.
            algorithm (Callable[[str, str], bool], optional): A custom search
            algorithm function
                that accepts the keyword and description and returns a boolean.
                Defaults to fuzzy matching.

        Returns:
            List[str]: A list of toolkit names whose descriptions match the
            keyword.
        """
        if algorithm is None:
            algorithm = self._default_search_algorithm

        matching_toolkits = []
        for name, func in self.toolkits.items():
            openai_func = OpenAIFunction(func)
            description = openai_func.get_function_description()
            if algorithm(keyword, description):
                matching_toolkits.append(name)

        return matching_toolkits
