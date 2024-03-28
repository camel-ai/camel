# Write Your Prompts with the `TextPrompt` Class

In this tutorial, we will explore the `TextPrompt` class and understand its functionalities. The `TextPrompt` class is a subclass of the built-in `str` class and provides additional features for working with text prompts. We will cover the following topics:

- Introduction to the `TextPrompt` class
- Using the `TextPrompt` class

## Introduction to the `TextPrompt` class

The `TextPrompt` class represents a text prompt and extends the functionality of the `str` class. It provides a property called `key_words`, which returns a set of strings representing the key words in the prompt.

Here's an example of how to use the `TextPrompt` class:

```python
from camel.prompts import TextPrompt

prompt = TextPrompt('Please enter your name and age: {name}, {age}')
print(prompt)  
>>> 'Please enter your name and age: {name}, {age}'
```

In the above example, we create a `TextPrompt` instance with a format string containing key words for name and age. We can print `TextPrompt` like Python `str`.

## Using the `TextPrompt` class

Once we have created a `TextPrompt` instance, we can use various methods and properties provided by the class to manipulate and work with the text prompt.

### The `key_words` property

The `key_words` property returns a set of strings representing the key words in the prompt.

```python
from camel.prompts import TextPrompt

prompt = TextPrompt('Please enter your name and age: {name}, {age}')
print(prompt.key_words)
>>> {'name', 'age'}
```

In the above example, the `key_words` property returns a set of strings representing the key words in the prompt, which in this case are 'name' and 'age'.

### The `format` method

The `format` method overrides the built-in `str.format` method to allow for partial formatting values in the format string. It replaces the key words in the format string with the provided values.

```python
from camel.prompts import TextPrompt

prompt = TextPrompt('Your name and age are: {name}, {age}')

name, age = 'John', 30
formatted_prompt = prompt.format(name=name, age=age)
print(formatted_prompt)  
>>> "Your name and age are: John, 30"
```

In the above example, we use the `format` method to replace the key words `{name}` and `{age}` with the values 'John' and 30, respectively.

We can also perform partial formatting by providing only some of the values:

```python
from camel.prompts import TextPrompt

prompt = TextPrompt('Your name and age are: {name}, {age}')

name = 'John'
partial_formatted_prompt = prompt.format(name=name)
print(partial_formatted_prompt)  
>>> "Your name and age are: John, {age}"
```

In the above example, we provide only the value for the `name` key word, while the `age` key word remains as it is. This will be helpful when we want to format different key words of `TextPrompt` in different agents.

### Manipulating `TextPrompt` instances

We can perform various string manipulation operations on `TextPrompt` instances, such as concatenation, joining, and applying string methods like Python `str`.

```python
from camel.prompts import TextPrompt

prompt1 = TextPrompt('Hello, {name}!')
prompt2 = TextPrompt('Welcome, {name}!')

# Concatenation
prompt3 = prompt1 + ' ' + prompt2
print(prompt3)  
>>> "Hello, {name}! Welcome, {name}!"

print(isinstance(prompt3, TextPrompt))
>>> True

print(prompt3.key_words)
>>> {'name'}

# Joining
prompt4 = TextPrompt(' ').join([prompt1, prompt2])
print(prompt4)
>>> "Hello, {name}! Welcome, {name}!"

print(isinstance(prompt4, TextPrompt))
>>> True

print(prompt4.key_words)
>>> {'name'}

# Applying string methods
prompt5 = prompt4.upper()
print(prompt5)
>>> "HELLO, {NAME}! WELCOME, {NAME}!"

print(isinstance(prompt5, TextPrompt))
>>> True

print(prompt5.key_words)
>>> {'NAME'}
```

In the above example, we demonstrate concatenation using the `+` operator, joining using the `join` method, and applying the `upper` method to a `TextPrompt` instance. The resulting prompts are also instances of `TextPrompt`.