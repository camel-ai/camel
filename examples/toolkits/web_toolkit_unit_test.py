import pytest
from camel.toolkits import WebToolkit

@pytest.fixture
def web_toolkit():
    return WebToolkit()


def test_1(web_toolkit):

    task_prompt = r"According to Girls Who Code, how long did it take in years for the percentage of computer scientists that were women to change by 13% from a starting point of 37%? Here are the reference website: `https://girlswhocode.com/about-us`"
    res = web_toolkit.stagehand_tool(task_prompt)

    assert '22' in str(res)


def test_2(web_toolkit):
    
    task_prompt = r"In Audre Lorde’s poem “Father Son and Holy Ghost”, what is the number of the stanza in which some lines are indented? Here are the reference website: `https://www.poetryfoundation.org/poems/46462/father-son-and-holy-ghost`"
    res = web_toolkit.stagehand_tool(task_prompt)

    assert '2' in str(res)


def test_3(web_toolkit):

    task_prompt = r"On the DeepFruits fruit detection graph on Connected Papers from 2016, what feature caused the largest bubble to be the size it is?"
    res = web_toolkit.stagehand_tool(task_prompt)

    assert "citations" in str(res)


def test_4(web_toolkit):

    task_prompt = "On Cornell Law School website's legal information institute, under the fifth section of federal rules alphabetically, what word was deleted in the last amendment to the first rule in the article that has \"witnesses\" in the most titles as of 2021?"
    res = web_toolkit.stagehand_tool(task_prompt)

    assert "inference" in str(res)


def test_5(web_toolkit):

    task_prompt = "Acording to `https://openreview.net/group?id=NeurIPS.cc/2022/Conference`, how many papers by an author named Yuri were accepted with a \"certain\" recommendation?"
    res = web_toolkit.stagehand_tool(task_prompt)

    assert "3" in str(res)
