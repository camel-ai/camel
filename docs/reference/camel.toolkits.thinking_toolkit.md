<a id="camel.toolkits.thinking_toolkit"></a>

<a id="camel.toolkits.thinking_toolkit.ThinkingToolkit"></a>

## ThinkingToolkit

```python
class ThinkingToolkit(BaseToolkit):
```

A toolkit for recording thoughts during reasoning processes.

<a id="camel.toolkits.thinking_toolkit.ThinkingToolkit.__init__"></a>

### __init__

```python
def __init__(self, timeout: Optional[float] = None):
```

Initialize the ThinkingToolkit.

**Parameters:**

- **timeout** (Optional[float]): The timeout for the toolkit. (default: :obj:`None`)

<a id="camel.toolkits.thinking_toolkit.ThinkingToolkit.plan"></a>

### plan

```python
def plan(self, plan: str):
```

Use the tool to create a plan or strategy.
This tool is for outlining the approach or steps to be taken before
starting the actual thinking process.

**Parameters:**

- **plan** (str): A forward-looking plan or strategy.

**Returns:**

  str: The recorded plan.

<a id="camel.toolkits.thinking_toolkit.ThinkingToolkit.hypothesize"></a>

### hypothesize

```python
def hypothesize(self, hypothesis: str):
```

Use the tool to form a hypothesis or make a prediction.
This tool is for making educated guesses or predictions based on
the plan, before detailed thinking.

**Parameters:**

- **hypothesis** (str): A hypothesis or prediction to test.

**Returns:**

  str: The recorded hypothesis.

<a id="camel.toolkits.thinking_toolkit.ThinkingToolkit.think"></a>

### think

```python
def think(self, thought: str):
```

Use the tool to think about something.
It will not obtain new information or change the database, but just
append the thought to the log. Use it for initial thoughts and
observations during the execution of the plan.

**Parameters:**

- **thought** (str): A thought to think about.

**Returns:**

  str: The recorded thought.

<a id="camel.toolkits.thinking_toolkit.ThinkingToolkit.contemplate"></a>

### contemplate

```python
def contemplate(self, contemplation: str):
```

Use the tool to deeply contemplate an idea or concept.
This tool is for deeper, more thorough exploration of thoughts,
considering multiple perspectives and implications. It's more
comprehensive than basic thinking but more focused than reflection.

**Parameters:**

- **contemplation** (str): A deeper exploration of thoughts or concepts.

**Returns:**

  str: The recorded contemplation.

<a id="camel.toolkits.thinking_toolkit.ThinkingToolkit.critique"></a>

### critique

```python
def critique(self, critique: str):
```

Use the tool to critically evaluate current thoughts.
This tool is for identifying potential flaws, biases, or
weaknesses in the current thinking process.

**Parameters:**

- **critique** (str): A critical evaluation of current thoughts.

**Returns:**

  str: The recorded critique.

<a id="camel.toolkits.thinking_toolkit.ThinkingToolkit.synthesize"></a>

### synthesize

```python
def synthesize(self, synthesis: str):
```

Use the tool to combine and integrate various thoughts.
This tool is for bringing together different thoughts, contemplations,
and critiques into a coherent understanding.

**Parameters:**

- **synthesis** (str): An integration of multiple thoughts and insights.

**Returns:**

  str: The recorded synthesis.

<a id="camel.toolkits.thinking_toolkit.ThinkingToolkit.reflect"></a>

### reflect

```python
def reflect(self, reflection: str):
```

Use the tool to reflect on the entire process.
This tool is for final evaluation of the entire thinking process,
including plans, hypotheses, thoughts, contemplations, critiques,
and syntheses.

**Parameters:**

- **reflection** (str): A comprehensive reflection on the process.

**Returns:**

  str: The recorded reflection.

<a id="camel.toolkits.thinking_toolkit.ThinkingToolkit.get_tools"></a>

### get_tools

```python
def get_tools(self):
```

**Returns:**

  List[FunctionTool]: A list of tools.
