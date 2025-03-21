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
from camel.toolkits import FileWriteToolkit
from camel.types import ModelPlatformType
from camel.types.enums import ModelType

# Create a model instance
model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
    model_config_dict={"temperature": 0},
)

# Define system message for the agent
sys_msg = "You are a helpful assistant that can create and modify files."

# Set up output directory
output_dir = "./file_write_outputs"
os.makedirs(output_dir, exist_ok=True)

# Initialize the FileWriteToolkit with the output directory
file_toolkit = FileWriteToolkit(output_dir=output_dir)

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
