import difflib
import importlib
import inspect
import pkgutil
from typing import Callable, List, Optional

from camel.toolkits.base import BaseToolkit
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

        self.toolkit_classes = {}
        self.toolkit_class_methods = {}

        self._load_toolkits()
        self._load_toolkit_class_and_methods()

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

    def _load_toolkit_class_and_methods(self):
        r"""
        Dynamically loads all classes and their methods from the `camel.toolkits` package.

        It iterates through all modules in the package, checking for public classes.
        For each class, it collects its public methods (those not starting with `_`).
        """
        package = importlib.import_module('camel.toolkits')

        for _, module_name, _ in pkgutil.iter_modules(package.__path__):
            module = importlib.import_module(f'camel.toolkits.{module_name}')

            for name, cls in inspect.getmembers(module, inspect.isclass):
                if cls.__module__ == module.__name__:
                    self.toolkit_classes[name] = cls

                    self.toolkit_class_methods[name] = {
                        method_name: method
                        for method_name, method in inspect.getmembers(
                            cls, inspect.isfunction
                        )
                        if callable(method) and hasattr(method, '_is_exported')
                    }

    def add_toolkit_from_function(self, toolkit_func: Callable):
        """
        Adds a toolkit function to the toolkits list.

        Parameters:
            toolkit_func (Callable): The toolkit function to be added.

        Returns:
            Str: A message indicating whether the addition was successful or
                if it  failed.
        """
        if not callable(toolkit_func):
            return "Provided argument is not a callable function."

        func_name = toolkit_func.__name__

        if not func_name:
            return "Function must have a valid name."

        self.toolkits[func_name] = toolkit_func

        return f"Toolkit '{func_name}' added successfully."

    def add_toolkit_from_instance(self, **kwargs):
        """
        Add a toolkit class instance to the tool list.

        Parameters:
            kwargs: The toolkit class instance to be added. Keyword arguments
                where each value is expected to be an instance of BaseToolkit.

        Returns:
            Str: A message indicating whether the addition was successful or
                if it failed.
        """
        messages = []
        for toolkit_instance_name, toolkit_instance in kwargs.items():
            if isinstance(toolkit_instance, BaseToolkit):
                for attr_name in dir(toolkit_instance):
                    attr = getattr(toolkit_instance, attr_name)

                    if callable(attr) and hasattr(attr, '_is_exported'):
                        method_name = f"{toolkit_instance_name}_{attr_name}"

                        self.toolkits[method_name] = attr
                        messages.append(f"Successfully added {method_name}.")
            else:
                messages.append(
                    f"Failed to add {toolkit_instance_name}: Not an instance of BaseToolkit."
                )

        return "\n".join(messages)

    def list_toolkits(self):
        r"""
        Lists the names of all available toolkits.

        Returns:
            List[str]: A list of all toolkit function names available for use.
        """
        return list(self.toolkits.keys())

    def list_toolkit_classes(self):
        r"""
        Lists the names of all available toolkit classes along with their
        methods.

        Returns:
            List[str]: A list of strings in the format 'ClassName: method1,
                method2, ...'.
        """
        result = []

        for class_name, methods in self.toolkit_class_methods.items():
            methods_str = ', '.join(methods)

            formatted_string = f"{class_name}: {methods_str}"

            result.append(formatted_string)

        return result

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
                toolkits.append(current_toolkit)
        if len(toolkits) > 0:
            return toolkits
        return "Toolkits are not found."

    def _default_search_algorithm(
        self, keyword: str, description: str
    ) -> bool:
        r"""
        Default search algorithm.

        Args:
            keyword (str): The keyword to search for.
            description (str): The description to search within.

        Returns:
            bool: True if a match is found based on similarity, False
            otherwise.
        """
        return keyword.lower() in description.lower()

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
            if algorithm(keyword, description) or algorithm(keyword, name):
                matching_toolkits.append(name)

        return matching_toolkits
