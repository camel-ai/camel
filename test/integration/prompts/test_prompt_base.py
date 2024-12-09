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

from camel.prompts.base import (
    CodePrompt,
    TextPrompt,
    TextPromptDict,
    return_prompt_wrapper,
    wrap_prompt_functions,
)


def test_return_prompt_wrapper():
    def my_function():
        return "Hello, world!"

    my_function = return_prompt_wrapper(TextPrompt, my_function)
    result = my_function()
    assert isinstance(result, TextPrompt)
    assert str(result) == "Hello, world!"


def test_return_prompt_wrapper_with_tuple():
    def my_function():
        return ("Hello, {name}!", "Welcome, {name}!")

    my_function = return_prompt_wrapper(TextPrompt, my_function)
    result = my_function()
    assert isinstance(result, tuple)
    assert all(isinstance(item, TextPrompt) for item in result)
    assert str(result[0]) == "Hello, {name}!"
    assert str(result[1]) == "Welcome, {name}!"


def test_wrap_prompt_functions():
    # Example class for testing
    class MyClass:
        def __init__(self, *args, **kwargs):
            pass

        def my_function(self):
            return "Hello, World!"

        def my_other_function(self):
            return "Goodbye, World!"

    # Decorate the class with the wrapper function
    @wrap_prompt_functions
    class MyDecoratedClass(MyClass):
        pass

    # Create an instance of the decorated class
    obj = MyDecoratedClass()

    # Check if the functions are wrapped correctly
    assert isinstance(obj.my_function(), MyDecoratedClass)
    assert isinstance(obj.my_other_function(), MyDecoratedClass)


def test_text_prompt_key_words():
    prompt = TextPrompt('Please enter your name and age: {name}, {age}')
    assert prompt.key_words == {'name', 'age'}

    prompt = prompt.format(name='John')
    assert prompt.key_words == {'age'}

    prompt = prompt.format(age=30)
    assert prompt.key_words == set()


def test_text_prompt_format():
    prompt = TextPrompt('Your name and age are: {name}, {age}')

    name, age = 'John', 30
    assert (
        prompt.format(name=name, age=age) == 'Your name and age are: John, 30'
    )

    # Partial formatting
    assert prompt.format(name=name) == 'Your name and age are: John, {age}'


def test_text_prompt_manipulate():
    prompt1 = TextPrompt('Hello, {name}!')
    prompt2 = TextPrompt('Welcome, {name}!')

    prompt3 = prompt1 + ' ' + prompt2
    assert prompt3 == 'Hello, {name}! Welcome, {name}!'
    assert isinstance(prompt3, TextPrompt)
    assert prompt3.key_words == {'name'}

    prompt4 = TextPrompt(' ').join([prompt1, prompt2])
    assert prompt4 == 'Hello, {name}! Welcome, {name}!'
    assert isinstance(prompt4, TextPrompt)
    assert prompt4.key_words == {'name'}

    prompt5 = prompt4.upper()
    assert prompt5 == 'HELLO, {NAME}! WELCOME, {NAME}!'
    assert isinstance(prompt5, TextPrompt)
    assert prompt5.key_words == {'NAME'}


def test_text_prompt_dict():
    prompt_dict = TextPromptDict()
    prompt_dict['test'] = TextPrompt('test')
    assert prompt_dict['test'] == TextPrompt('test')


def test_code_prompt_initialization():
    code_prompt = CodePrompt("print('Hello, World!')", code_type="python")
    assert code_prompt == "print('Hello, World!')"
    assert code_prompt.code_type == "python"


def test_code_prompt_missing_code_type():
    code_prompt = CodePrompt("print('Hello, World!')")
    assert code_prompt.code_type is None


def test_code_prompt_set_code_type():
    code_prompt = CodePrompt("print('Hello, World!')")
    code_prompt.set_code_type("python")
    assert code_prompt.code_type == "python"


def test_code_prompt_execute(monkeypatch):
    monkeypatch.setattr('builtins.input', lambda _: 'Y')
    code_prompt = CodePrompt(
        "a = 1\nprint('Hello, World!')", code_type="python"
    )
    result = code_prompt.execute()
    assert result == "Hello, World!\n"


def test_code_prompt_execute_error(monkeypatch):
    monkeypatch.setattr('builtins.input', lambda _: "Y")
    code_prompt = CodePrompt("print('Hello, World!'", code_type="python")
    result = code_prompt.execute()
    assert "SyntaxError:" in result
