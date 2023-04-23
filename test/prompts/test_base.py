from camel.prompts import TextPrompt, TextPromptDict


def test_text_prompt_key_words():
    prompt = TextPrompt('Please enter your name and age: {name}, {age}')
    assert prompt.key_words == {'name', 'age'}

    prompt = TextPrompt('Please enter your email address')
    assert prompt.key_words == set()


def test_text_prompt_format():
    prompt = TextPrompt('Your name and age are: {name}, {age}')

    name, age = 'John', 30
    assert prompt.format(name=name,
                         age=age) == 'Your name and age are: John, 30'

    assert prompt.format(name=name) == 'Your name and age are: John, {age}'


def test_text_prompt_dict():
    prompt_dict = TextPromptDict()
    prompt_dict['test'] = TextPrompt('test')
    assert prompt_dict['test'] == TextPrompt('test')
