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
# ruff: noqa: E501
import os

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import FileToolkit
from camel.types import ModelPlatformType
from camel.types.enums import ModelType

# Create a model instance
model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)

# Define system message for the agent
sys_msg = "You are a helpful assistant that can create and modify files."

# Set up output directory
working_directory = "./file_write_outputs"
os.makedirs(working_directory, exist_ok=True)

# Initialize the FileWriteToolkit with the output directory
file_toolkit = FileToolkit(working_directory=working_directory)

# Get the tools from the toolkit
tools_list = file_toolkit.get_tools()

# Initialize a ChatAgent with the tools
camel_agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=tools_list,
)

# Example 1: Write a Python script to a file
python_query = """Please generate a Python script that creates a simple
                  web server using Flask and save it to a file."""

camel_agent.reset()
response = camel_agent.step(python_query)
print("Example 1: Writing a Python script")
print(response.msgs[0].content)
print("Tool calls:", response.info['tool_calls'])
print("\n")
'''
===============================================================================
Example 1: Writing a Python script
The Python script for a simple web server using Flask has been created and saved as `simple_flask_server.py`. You can run this script to start the server, and it will return "Hello, Flask!" when accessed at the root URL.
Tool calls: [ToolCallingRecord(tool_name='write_to_file', args={'content': 'from flask import Flask\n\napp = Flask(__name__)\n\n@app.route(\'/\')\ndef home():\n    return "Hello, Flask!"\n\nif __name__ == \'__main__\':\n    app.run(debug=True)', 'filename': 'simple_flask_server.py', 'encoding': 'utf-8'}, result='Content successfully written to file: /Users/enrei/Desktop/camel0209/camel/file_write_outputs/simple_flask_server.py', tool_call_id='call_hCCxkjNkx4HKN9q6fuIpe8Bn')]
===============================================================================
'''

# Example 2: Create a JSON data file
json_query = """Generate a JSON file containing information about 3 fictional
                books, including title, author, publication year, and genre."""
camel_agent.reset()
response = camel_agent.step(json_query)
print("Example 2: Creating a JSON file")
print(response.msgs[0].content)
print("Tool calls:", response.info['tool_calls'])
print("\n")
'''
===============================================================================
Example 2: Creating a JSON file
The JSON file containing information about three fictional books has been successfully created. You can find it at the following location: **books.json**.

Here is the content of the file:

```json
[
  {
    "title": "The Whispering Shadows",
    "author": "Ava Sinclair",
    "publication_year": 2021,
    "genre": "Fantasy"
  },
  {
    "title": "Echoes of the Past",
    "author": "Liam Carter",
    "publication_year": 2019,
    "genre": "Historical Fiction"
  },
  {
    "title": "The Last Star",
    "author": "Maya Thompson",
    "publication_year": 2022,
    "genre": "Science Fiction"
  }
]
```
Tool calls: [ToolCallingRecord(tool_name='write_to_file', args={'content': '[  \n  {  \n    "title": "The Whispering Shadows",  \n    "author": "Ava Sinclair",  \n    "publication_year": 2021,  \n    "genre": "Fantasy"  \n  },  \n  {  \n    "title": "Echoes of the Past",  \n    "author": "Liam Carter",  \n    "publication_year": 2019,  \n    "genre": "Historical Fiction"  \n  },  \n  {  \n    "title": "The Last Star",  \n    "author": "Maya Thompson",  \n    "publication_year": 2022,  \n    "genre": "Science Fiction"  \n  }  \n]', 'filename': 'books.json', 'encoding': 'utf-8'}, result='Content successfully written to file: /Users/enrei/Desktop/camel0209/camel/file_write_outputs/books.json', tool_call_id='call_1ayRgujHhiWowz0jhtMCukgn')]
===============================================================================
'''

# Example 3: Create a CSV file with tabular data
csv_query = """Create a CSV file with data about 5 countries, including
               columns for name, capital, population, area, and continent."""
camel_agent.reset()
response = camel_agent.step(csv_query)
print("Example 3: Creating a CSV file")
print(response.msgs[0].content)
print("Tool calls:", response.info['tool_calls'])
print("\n")
'''
===============================================================================
Example 3: Creating a CSV file
The CSV file containing data about 5 countries has been successfully created. It includes the following columns: name, capital, population, area, and continent. If you need any further modifications or additional data, feel free to ask!
Tool calls: [ToolCallingRecord(tool_name='write_to_file', args={'content': [['Name', 'Capital', 'Population', 'Area (sq km)', 'Continent'], ['United States', 'Washington, D.C.', '331002651', '9833517', 'North America'], ['Brazil', 'Brasília', '212559417', '8515767', 'South America'], ['Germany', 'Berlin', '83783942', '357022', 'Europe'], ['Australia', 'Canberra', '25499884', '7692024', 'Oceania'], ['Japan', 'Tokyo', '126476461', '377975', 'Asia']], 'filename': 'countries_data.csv', 'encoding': 'utf-8'}, result='Content successfully written to file: /Users/enrei/Desktop/camel0209/camel/file_write_outputs/countries_data.csv', tool_call_id='call_yTgErI2TrV32ehs5LJCf6kW7')]
===============================================================================
'''

# Example 4: Create a Markdown document
md_query = """Write a markdown document that explains the basics of machine
              learning, including headings, bullet points, and code examples.
              """
camel_agent.reset()
response = camel_agent.step(md_query)
print("Example 4: Creating a Markdown document")
print(response.msgs[0].content)
print("Tool calls:", response.info['tool_calls'])
print("\n")
'''
===============================================================================
Example 4: Creating a Markdown document
The markdown document explaining the basics of machine learning has been successfully created. You can find it under the name **basics_of_machine_learning.md**. If you need any further modifications or additional information, feel free to ask!
Tool calls: [ToolCallingRecord(tool_name='write_to_file', args={'content': "# Basics of Machine Learning\n\nMachine Learning (ML) is a subset of artificial intelligence (AI) that focuses on building systems that learn from data and improve their performance over time without being explicitly programmed. Here are the key concepts and components of machine learning:\n\n## Key Concepts\n\n- **Data**: The foundation of machine learning. Data can be structured (like tables) or unstructured (like images or text).\n- **Model**: A mathematical representation of a process that is trained on data to make predictions or decisions.\n- **Training**: The process of feeding data into a model to help it learn patterns.\n- **Testing**: Evaluating the model's performance on unseen data to ensure it generalizes well.\n- **Features**: Individual measurable properties or characteristics used as input to the model.\n- **Labels**: The output or target variable that the model is trying to predict.\n\n## Types of Machine Learning\n\n1. **Supervised Learning**: The model is trained on labeled data.\n   - **Examples**: Classification, Regression\n   - **Use Cases**: Spam detection, House price prediction\n\n2. **Unsupervised Learning**: The model is trained on unlabeled data and tries to find patterns.\n   - **Examples**: Clustering, Dimensionality Reduction\n   - **Use Cases**: Customer segmentation, Anomaly detection\n\n3. **Reinforcement Learning**: The model learns by interacting with an environment and receiving feedback.\n   - **Examples**: Game playing, Robotics\n   - **Use Cases**: Self-driving cars, Game AI\n\n## Machine Learning Workflow\n\n1. **Data Collection**: Gather data from various sources.\n2. **Data Preprocessing**: Clean and prepare the data for analysis.\n3. **Model Selection**: Choose the appropriate algorithm for the task.\n4. **Training the Model**: Fit the model to the training data.\n5. **Model Evaluation**: Assess the model's performance using metrics like accuracy, precision, and recall.\n6. **Hyperparameter Tuning**: Optimize the model's parameters for better performance.\n7. **Deployment**: Implement the model in a production environment.\n\n## Code Example\n\nHere is a simple example of a supervised learning model using Python and the popular library `scikit-learn`:\n\n```python\n# Import necessary libraries\nimport numpy as np\nimport pandas as pd\nfrom sklearn.model_selection import train_test_split\nfrom sklearn.linear_model import LinearRegression\nfrom sklearn.metrics import mean_squared_error\n\n# Load dataset\ndata = pd.read_csv('data.csv')\n\n# Define features and labels\nX = data[['feature1', 'feature2']]\nY = data['label']\n\n# Split the data into training and testing sets\nX_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.2, random_state=42)\n\n# Create a model\nmodel = LinearRegression()\n\n# Train the model\nmodel.fit(X_train, Y_train)\n\n# Make predictions\npredictions = model.predict(X_test)\n\n# Evaluate the model\nmse = mean_squared_error(Y_test, predictions)\nprint(f'Mean Squared Error: {mse}')\n```\n\n## Conclusion\n\nMachine learning is a powerful tool that can be applied to various fields, from healthcare to finance. Understanding the basics of machine learning is essential for anyone looking to leverage data for decision-making and predictive analytics.", 'filename': 'basics_of_machine_learning.md', 'encoding': 'utf-8'}, result='Content successfully written to file: /Users/enrei/Desktop/camel0209/camel/file_write_outputs/basics_of_machine_learning.md', tool_call_id='call_KKHcbPvmG8VWc4W2JeOWcg1B')]
===============================================================================
'''

# Example 5: Create a YAML configuration file
yaml_query = """Generate a YAML configuration file for a web application
                with settings for database connection, logging, and server
                parameters."""
camel_agent.reset()
response = camel_agent.step(yaml_query)
print("Example 5: Creating a YAML configuration file")
print(response.msgs[0].content)
print("Tool calls:", response.info['tool_calls'])
print("\n")
'''
===============================================================================
Example 5: Creating a YAML configuration file
The YAML configuration file for the web application has been successfully created. Here are the contents of the file:

```yaml
database:
  host: localhost
  port: 5432
  username: user
  password: password
  dbname: mydatabase

logging:
  level: info
  file: /var/log/myapp.log
  max_size: 10MB
  max_backups: 5

server:
  host: 0.0.0.0
  port: 8080
  timeout: 30s
  enable_https: true
```

The file is saved as `config.yaml`. If you need any modifications or additional settings, feel free to ask!
Tool calls: [ToolCallingRecord(tool_name='write_to_file', args={'content': 'database:\n  host: localhost\n  port: 5432\n  username: user\n  password: password\n  dbname: mydatabase\n\nlogging:\n  level: info\n  file: /var/log/myapp.log\n  max_size: 10MB\n  max_backups: 5\n\nserver:\n  host: 0.0.0.0\n  port: 8080\n  timeout: 30s\n  enable_https: true\n', 'filename': 'config.yaml', 'encoding': 'utf-8'}, result='Content successfully written to file: /Users/enrei/Desktop/camel0209/camel/file_write_outputs/config.yaml', tool_call_id='call_svQbTh8tl1diDDYwxNDWUp2U')]
===============================================================================
'''

# Example 6: Create an HTML file
html_query = """Create a simple HTML webpage with a header, navigation menu,
                main content section, and footer."""
camel_agent.reset()
response = camel_agent.step(html_query)
print("Example 6: Creating an HTML file")
print(response.msgs[0].content)
print("Tool calls:", response.info['tool_calls'])
print("\n")
'''
===============================================================================
Example 6: Creating an HTML file
I have created a simple HTML webpage with a header, navigation menu, main content section, and footer. You can find the file named `simple_webpage.html` in the specified directory. If you need any modifications or additional features, feel free to ask!
Tool calls: [ToolCallingRecord(tool_name='write_to_file', args={'content': '<!DOCTYPE html>\n<html lang="en">\n<head>\n    <meta charset="UTF-8">\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n    <title>Simple Webpage</title>\n    <link rel="stylesheet" href="styles.css">\n</head>\n<body>\n    <header>\n        <h1>Welcome to My Simple Webpage</h1>\n    </header>\n    <nav>\n        <ul>\n            <li><a href="#home">Home</a></li>\n            <li><a href="#about">About</a></li>\n            <li><a href="#services">Services</a></li>\n            <li><a href="#contact">Contact</a></li>\n        </ul>\n    </nav>\n    <main>\n        <section id="home">\n            <h2>Home</h2>\n            <p>This is the home section of the webpage.</p>\n        </section>\n        <section id="about">\n            <h2>About</h2>\n            <p>This section contains information about us.</p>\n        </section>\n        <section id="services">\n            <h2>Services</h2>\n            <p>Details about our services can be found here.</p>\n        </section>\n        <section id="contact">\n            <h2>Contact</h2>\n            <p>Get in touch with us through this section.</p>\n        </section>\n    </main>\n    <footer>\n        <p>&copy; 2023 My Simple Webpage. All rights reserved.</p>\n    </footer>\n</body>\n</html>', 'filename': 'simple_webpage.html', 'encoding': 'utf-8'}, result='Content successfully written to file: /Users/enrei/Desktop/camel0209/camel/file_write_outputs/simple_webpage.html', tool_call_id='call_6FUwTx4gSAB8mtN7lety05SP')]
===============================================================================
'''

# Example 7: Please give me a pdf file with formulas of advanced mathematics
latex_pdf_query = (
    """Please give me a pdf file with formulas of advanced mathematics."""
)

camel_agent.reset()
response = camel_agent.step(latex_pdf_query)
print(f"Example 7: {latex_pdf_query}")
print(response.msgs[0].content)
print("Tool calls:", response.info['tool_calls'])
print("\n")
'''
===============================================================================
......
Download Advanced Mathematics Formulas
PDF](sandbox:/Users/yifengwang/project/camel/file_write_outputs/advanced_mathematics_formulas.pdf)
Tool calls: [ToolCallingRecord(tool_name='write_to_file', args={'content': "#
Advanced Mathematics Formulas\n\n## 1. Calculus\n### 1.1 Derivatives\n- Power
Rule:  \\( \\frac{d}{dx} x^n = n x^{n-1} \\)\n- Product Rule:  \\(
\\frac{d}{dx} [u v] = u' v + u v' \\)\n- Quotient Rule:  \\( \\frac{d}{dx}
\\left[ \\frac{u}{v} \\right] = \\frac{u' v - u v'}{v^2} \\)\n- Chain Rule:
\\( \\frac{d}{dx} f(g(x)) = f'(g(x)) g'(x) \\)\n\n### 1.2 Integrals\n-
Indefinite Integral:  \\( \\int x^n \\, dx = \\frac{x^{n+1}}{n+1} + C \\) (for
\\( n \\neq -1 \\))\n- Definite Integral:  \\( \\int_a^b f(x) \\, dx = F(b) -
F(a) \\) where \\( F \\) is the antiderivative of \\( f \\)\n\n## 2. Linear
Algebra\n### 2.1 Matrices\n- Matrix Addition:  \\( A + B = [a_{ij} + b_{ij}]
\\)\n- Matrix Multiplication:  \\( C = AB \\) where \\( c_{ij} = \\sum_k a_{ik}
b_{kj} \\)\n- Determinant of a 2x2 Matrix:  \\( \\text{det}(A) = ad - bc \\)
for \\( A = \\begin{pmatrix} a & b \\\\ c & d \\end{pmatrix} \\)\n\n## 3.
Differential Equations\n- First Order Linear DE:  \\( \\frac{dy}{dx} + P(x)y =
Q(x) \\)\n- Second Order Linear DE:  \\( y'' + p(x)y' + q(x)y = 0 \\)\n\n## 4.
Complex Numbers\n- Euler's Formula:  \\( e^{ix} = \\cos(x) + i\\sin(x) \\)\n-
Polar Form:  \\( z = re^{i\\theta} \\) where \\( r = |z| \\) and \\( \\theta =
\\arg(z) \\)\n\n## 5. Probability and Statistics\n- Mean:  \\( \\mu =
\\frac{1}{N} \\sum_{i=1}^N x_i \\)\n- Variance:  \\( \\sigma^2 = \\frac{1}{N}
\\sum_{i=1}^N (x_i - \\mu)^2 \\)\n- Standard Deviation:  \\( \\sigma =
\\sqrt{\\sigma^2} \\)\n\n## 6. Number Theory\n- Fundamental Theorem of
Arithmetic: Every integer greater than 1 can be expressed as a product of prime
numbers.\n- Euclidean Algorithm: To find the GCD of two integers \\( a \\) and
\\( b \\), repeatedly apply \\( a = bq + r \\) until \\( r = 0 \\).\n\n## 7.
Set Theory\n- Union:  \\( A \\cup B = \\{ x | x \\in A \\text{ or } x \\in B
\\} \\)\n- Intersection:  \\( A \\cap B = \\{ x | x \\in A \\text{ and } x \\in
B \\} \\)\n- Complement:  \\( A' = \\{ x | x \\notin A \\} \\)\n\n##
Conclusion\nThese formulas cover various branches of advanced mathematics,
providing a foundation for further study and application.", 'filename':
'advanced_mathematics_formulas.pdf', 'encoding': None, 'use_latex': True},
result="Error occurred while writing to file
/Users/yifengwang/project/camel/file_write_outputs/advanced_mathematics_formulas.pdf:
Command '['latexmk', '--pdf', '--interaction=nonstopmode',
'/Users/yifengwang/project/camel/file_write_outputs/advanced_mathematics_formulas.pdf.tex']'
returned non-zero exit status 12.",
tool_call_id='call_xBpaH5YPU27mCEwjg4i2LlBC'),
ToolCallingRecord(tool_name='write_to_file', args={'content': "# Advanced
Mathematics Formulas\n\n## 1. Calculus\n### 1.1 Derivatives\n- Power Rule:  \\(
\\frac{d}{dx} x^n = n x^{n-1} \\)\n- Product Rule:  \\( \\frac{d}{dx} [u v] =
u' v + u v' \\)\n- Quotient Rule:  \\( \\frac{d}{dx} \\left[ \\frac{u}{v}
\\right] = \\frac{u' v - u v'}{v^2} \\)\n- Chain Rule:  \\( \\frac{d}{dx}
f(g(x)) = f'(g(x)) g'(x) \\)\n\n### 1.2 Integrals\n- Indefinite Integral:  \\(
\\int x^n \\, dx = \\frac{x^{n+1}}{n+1} + C \\) (for \\( n \\neq -1 \\))\n-
Definite Integral:  \\( \\int_a^b f(x) \\, dx = F(b) - F(a) \\) where \\( F \\)
is the antiderivative of \\( f \\)\n\n## 2. Linear Algebra\n### 2.1 Matrices\n-
Matrix Addition:  \\( A + B = [a_{ij} + b_{ij}] \\)\n- Matrix Multiplication:
\\( C = AB \\) where \\( c_{ij} = \\sum_k a_{ik} b_{kj} \\)\n- Determinant of a
2x2 Matrix:  \\( \\text{det}(A) = ad - bc \\) for \\( A = \\begin{pmatrix} a &
b \\\\ c & d \\end{pmatrix} \\)\n\n## 3. Differential Equations\n- First Order
Linear DE:  \\( \\frac{dy}{dx} + P(x)y = Q(x) \\)\n- Second Order Linear DE:
\\( y'' + p(x)y' + q(x)y = 0 \\)\n\n## 4. Complex Numbers\n- Euler's Formula:
\\( e^{ix} = \\cos(x) + i\\sin(x) \\)\n- Polar Form:  \\( z = re^{i\\theta} \\)
where \\( r = |z| \\) and \\( \\theta = \\arg(z) \\)\n\n## 5. Probability and
Statistics\n- Mean:  \\( \\mu = \\frac{1}{N} \\sum_{i=1}^N x_i \\)\n- Variance:
\\( \\sigma^2 = \\frac{1}{N} \\sum_{i=1}^N (x_i - \\mu)^2 \\)\n- Standard
Deviation:  \\( \\sigma = \\sqrt{\\sigma^2} \\)\n\n## 6. Number Theory\n-
Fundamental Theorem of Arithmetic: Every integer greater than 1 can be
expressed as a product of prime numbers.\n- Euclidean Algorithm: To find the
GCD of two integers \\( a \\) and \\( b \\), repeatedly apply \\( a = bq + r
\\) until \\( r = 0 \\).\n\n## 7. Set Theory\n- Union:  \\( A \\cup B = \\{ x |
x \\in A \\text{ or } x \\in B \\} \\)\n- Intersection:  \\( A \\cap B = \\{ x
| x \\in A \\text{ and } x \\in B \\} \\)\n- Complement:  \\( A' = \\{ x | x
\\notin A \\} \\)\n\n## Conclusion\nThese formulas cover various branches of
advanced mathematics, providing a foundation for further study and
application.", 'filename': 'advanced_mathematics_formulas.pdf', 'encoding':
None, 'use_latex': False}, result='Content successfully written to file:
/Users/yifengwang/project/camel/file_write_outputs/advanced_mathematics_formulas.pdf',
tool_call_id='call_uKqOpAl5Wm1O8dUYJc5yZf4U')]
===============================================================================
'''

# Example 8: what is multiagent? please export them as pdf file
pdf_query = """what is multiagent? Please export them as pdf file"""

camel_agent.reset()
response = camel_agent.step(pdf_query)
print(f"Example 8: {pdf_query}")
print(response.msgs[0].content)
print("Tool calls:", response.info['tool_calls'])
print("\n")

'''
===============================================================================
Example 8: what is multiagent? please export them as pdf file
The information about multiagent systems has been successfully exported to a PDF file named "multiagent_overview.pdf". If you need any further assistance, feel free to ask!
Tool calls: [ToolCallingRecord(tool_name='write_to_file', args={'content': '### What is Multiagent?\n\nMultiagent systems (MAS) are systems composed of multiple interacting intelligent agents.
These agents can be software programs, robots, or any entities that can perceive their environment and act upon it. The key characteristics of multiagent systems include:\n\n
1. **Autonomy**: Each agent operates independently and makes its own decisions.\n2. **Social Ability**: Agents can communicate and interact with each other to achieve their goals.
\n3. **Reactivity**: Agents can respond to changes in their environment in real-time.\n4. **Proactiveness**: Agents can take initiative and act in anticipation of future events.\n\n
### Applications of Multiagent Systems\n\nMultiagent systems are used in various fields, including:\n- **Robotics**: Coordinating multiple robots to perform tasks.\n- **Distributed Control**:
# Managing resources in smart grids or traffic systems.\n- **Game Theory**: Analyzing strategies in competitive environments.\n- **Simulation**: Modeling complex systems in economics, biology,
# and social sciences.\n\n### Conclusion\n\nMultiagent systems provide a framework for understanding and designing systems where multiple agents interact, leading to complex behaviors and solutions to problems that are difficult for a single agent to solve alone.',
#  'filename': 'multiagent_overview.pdf', 'encoding': None, 'use_latex': False}, result='Content successfully written to file: /Users/yifengwang/project/camel/file_write_outputs/multiagent_overview.pdf', tool_call_id='call_btYqjycX4aUfBNJUy8bpnHSV')]
===============================================================================
'''

# Example 9: Read file content
read_query = """Please read the content of the web server python file that was created earlier."""

camel_agent.reset()
response = camel_agent.step(read_query)
print("Example 9: Reading file content")
print(response.msgs[0].content)
print("Tool calls:", response.info['tool_calls'])
print("\n")

'''
===============================================================================
Example 9: Reading file content
Here is the content of the `simple_flask_server.py` file:

```python
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Hello, Flask!"

if __name__ == '__main__':
    app.run(debug=True)
```

This is a simple Flask web server that returns "Hello, Flask!" when accessed at the root URL.
Tool calls: [ToolCallingRecord(tool_name='read_file', args={'file_path': 'simple_flask_server.py'}, result='from flask import Flask\n\napp = Flask(__name__)\n\n@app.route(\'/\')\ndef home():\n    return "Hello, Flask!"\n\nif __name__ == \'__main__\':\n    app.run(debug=True)', tool_call_id='call_abc123def456')]
===============================================================================
'''

# Example 10: Edit file content
edit_query = """Please edit the simple_flask_server.py file to add a new route '/about' that returns 'About Flask Server'."""

camel_agent.reset()
response = camel_agent.step(edit_query)
print("Example 10: Editing file content")
print(response.msgs[0].content)
print("Tool calls:", response.info['tool_calls'])
print("\n")

'''
===============================================================================
Example 10: Editing file content
I have successfully edited the `simple_flask_server.py` file to add a new route '/about' that returns 'About Flask Server'. The file now includes both the original home route and the new about route.
Tool calls: [ToolCallingRecord(tool_name='edit_file', args={'file_path': 'simple_flask_server.py', 'old_content': '@app.route(\'/\')\ndef home():\n    return "Hello, Flask!"\n\nif __name__ == \'__main__\':', 'new_content': '@app.route(\'/\')\ndef home():\n    return "Hello, Flask!"\n\n@app.route(\'/about\')\ndef about():\n    return "About Flask Server"\n\nif __name__ == \'__main__\':'}, result='Successfully edited file: /Users/enrei/Desktop/camel0209/camel/file_write_outputs/simple_flask_server.py', tool_call_id='call_def789ghi012')]
===============================================================================
'''

# Example 11: Insert content at specific line
insert_query = """Please insert a comment '# This is a simple Flask application' at the beginning of the simple_flask_server.py file."""

camel_agent.reset()
response = camel_agent.step(insert_query)
print("Example 11: Inserting content at specific line")
print(response.msgs[0].content)
print("Tool calls:", response.info['tool_calls'])
print("\n")

'''
===============================================================================
Example 11: Inserting content at specific line
I have successfully inserted the comment '# This is a simple Flask application' at the beginning of the `simple_flask_server.py` file. The comment has been added as the first line of the file.
Tool calls: [ToolCallingRecord(tool_name='insert_at_line', args={'file_path': 'simple_flask_server.py', 'content': '# This is a simple Flask application', 'line_number': 0}, result='Successfully inserted content at line 0 in /Users/enrei/Desktop/camel0209/camel/file_write_outputs/simple_flask_server.py', tool_call_id='call_jkl345mno678')]
===============================================================================
'''

# Example 12: Read and edit JSON file
json_edit_query = """Please read the books.json file, then edit it to add a new book with title 'The Future of AI', author 'Dr. Smith', publication year 2023, and genre 'Science Fiction'."""

camel_agent.reset()
response = camel_agent.step(json_edit_query)
print("Example 12: Reading and editing JSON file")
print(response.msgs[0].content)
print("Tool calls:", response.info['tool_calls'])
print("\n")

'''
===============================================================================
Example 12: Reading and editing JSON file
I have successfully read the books.json file and added a new book entry. The file now contains 4 books including the newly added "The Future of AI" by Dr. Smith.
Tool calls: [ToolCallingRecord(tool_name='read_file', args={'file_path': 'books.json'}, result='[\n  {\n    "title": "The Whispering Shadows",\n    "author": "Ava Sinclair",\n    "publication_year": 2021,\n    "genre": "Fantasy"\n  },\n  {\n    "title": "Echoes of the Past",\n    "author": "Liam Carter",\n    "publication_year": 2019,\n    "genre": "Historical Fiction"\n  },\n  {\n    "title": "The Last Star",\n    "author": "Maya Thompson",\n    "publication_year": 2022,\n    "genre": "Science Fiction"\n  }\n]', tool_call_id='call_pqr901stu234'), ToolCallingRecord(tool_name='edit_file', args={'file_path': 'books.json', 'old_content': '  }\n]', 'new_content': '  },\n  {\n    "title": "The Future of AI",\n    "author": "Dr. Smith",\n    "publication_year": 2023,\n    "genre": "Science Fiction"\n  }\n]'}, result='Successfully edited file: /Users/enrei/Desktop/camel0209/camel/file_write_outputs/books.json', tool_call_id='call_vwx567yza890')]
===============================================================================
'''

# Example 13: Insert at end of file
insert_end_query = """Please insert a new route '/contact' that returns 'Contact us at contact@example.com' at the end of the simple_flask_server.py file, just before the 'if __name__ == \'__main__\':' line."""

camel_agent.reset()
response = camel_agent.step(insert_end_query)
print("Example 13: Inserting at end of file")
print(response.msgs[0].content)
print("Tool calls:", response.info['tool_calls'])
print("\n")

'''
===============================================================================
Example 13: Inserting at end of file
I have successfully inserted the new '/contact' route in the `simple_flask_server.py` file. The route has been added just before the main execution block, so the file now has three routes: '/', '/about', and '/contact'.
Tool calls: [ToolCallingRecord(tool_name='insert_at_line', args={'file_path': 'simple_flask_server.py', 'content': '@app.route(\'/contact\')\ndef contact():\n    return "Contact us at contact@example.com"', 'line_number': -2}, result='Successfully inserted content at line -2 in /Users/enrei/Desktop/camel0209/camel/file_write_outputs/simple_flask_server.py', tool_call_id='call_bcd123efg456')]
===============================================================================
'''

# Example 14: Read the final modified file
final_read_query = """Please read the final content of the simple_flask_server.py file to see all the modifications we made."""

camel_agent.reset()
response = camel_agent.step(final_read_query)
print("Example 14: Reading final modified file")
print(response.msgs[0].content)
print("Tool calls:", response.info['tool_calls'])
print("\n")

'''
===============================================================================
Example 14: Reading final modified file
Here is the final content of the `simple_flask_server.py` file after all our modifications:

```python
# This is a simple Flask application
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Hello, Flask!"

@app.route('/about')
def about():
    return "About Flask Server"

@app.route('/contact')
def contact():
    return "Contact us at contact@example.com"

if __name__ == '__main__':
    app.run(debug=True)
```

The file now includes:
1. A comment at the top
2. Three routes: '/', '/about', and '/contact'
3. All the original functionality plus the new features we added
Tool calls: [ToolCallingRecord(tool_name='read_file', args={'file_path': 'simple_flask_server.py'}, result='# This is a simple Flask application\nfrom flask import Flask\n\napp = Flask(__name__)\n\n@app.route(\'/\')\ndef home():\n    return "Hello, Flask!"\n\n@app.route(\'/about\')\ndef about():\n    return "About Flask Server"\n\n@app.route(\'/contact\')\ndef contact():\n    return "Contact us at contact@example.com"\n\nif __name__ == \'__main__\':\n    app.run(debug=True)', tool_call_id='call_hij789klm012')]
===============================================================================
'''
