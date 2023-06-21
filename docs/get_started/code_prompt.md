# Introduction to `CodePrompt` Class

In this tutorial, we will explore the `CodePrompt` class, which is a class that represents a code prompt. It extends the `TextPrompt` class, which in turn extends the built-in `str` class. The `CodePrompt` class provides additional functionality related to code execution and handling.

## Importing the `CodePrompt` Class

To use the `CodePrompt` class, you need to import it. Here's an example of how to import the class:

```python
from camel.prompts import CodePrompt
```

## Creating a `CodePrompt` Instance

To create a `CodePrompt` instance, you can simply instantiate the class, providing the code string and the code type as an input argument.

```python
code_prompt = CodePrompt("print('Hello, World!')", code_type="python")
```

In this example, we create a `CodePrompt` instance with the code string `"print('Hello, World!')"`. We also specify the code type as `"python"`. The code type can be set to `None` if not needed.

## Accessing the Code and Code Type

Once you have a `CodePrompt` instance, you can access the code string and code type as following:

- `code_prompt`: Accesses the code string of the prompt.
- `code_type`: Accesses the type of code associated with the prompt.

```python
print(code_prompt)
>>> "print('Hello, World!')"

print(code_prompt.code_type)
>>> "python"
```

## Modifying the Code Type

If you need to change the code type associated with a `CodePrompt` instance, you can use the `set_code_type` method. This method takes a code type as a parameter and updates the code type of the instance.

```python
code_prompt = CodePrompt("print('Hello, World!')")
print(code_prompt.code_type)
>>> None

code_prompt.set_code_type("python")
print(code_prompt.code_type) 
>>> "python"
```

In this example, we change the code type of the `CodePrompt` instance from `None` to `"python"`.

## Executing the Code

The `CodePrompt` class provides a method called `execute` that allows you to execute the code string associated with the prompt. It returns a tuple containing the output string and local variables.

```python
CodePrompt("a = 1\nprint('Hello, World!')", code_type="python")
output, variables = code_prompt.execute()
print(output)
>>> "Hello, World!\n"

print(variables)
>>> {"a": 1}
```

In this example, we execute the code prompt and store the output string in the `output` variable and the local variables in the `variables` dictionary.

## Handling Execution Errors

If there is an error during the code execution, the `execute` method catches the error and returns the traceback string. If there is no error, the method returns the output string and local variables.

```python
code_prompt = CodePrompt("print('Hello, World!'")
traceback_str, _ = code_prompt.execute()
assert "SyntaxError" in traceback_str
>>> True
```

In this example, the code string has a syntax error where a right bracket `)` is missing, and the `execute` method returns the traceback string indicating the error.

That's it! You have went through the basics of using the `CodePrompt` class. You can now create code prompts, access the code and code type, modify the code type if needed, and execute the code.