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
import apps.agents.text_utils as text_utils


def test_split_markdown_code_newline():
    inp = (
        "Solution: To preprocess the historical stock data, we "
        "can perform the following steps:\n\n1. Remove any unnecessary"
        " columns that do not contribute to the prediction, such as"
        " the stock symbol or date.\n2. Check for and handle any "
        "missing or null values in the data.\n3. Normalize the data"
        " to ensure that all features are on the same scale. This "
        "can be done using techniques such as Min-Max scaling or "
        "Z-score normalization.\n4. Split the data into training "
        "and testing sets. The training set will be used to train "
        "the machine learning model, while the testing set will be "
        "used to evaluate its performance.\n\nHere is an example "
        "code snippet to preprocess the data using Pandas:\n\n```\n"
        "import pandas as pd\nfrom sklearn.preprocessing import "
        "MinMaxScaler\nfrom sklearn.model_selection import "
        "train_test_split\n\n# Read in the historical stock data\ndata"
        " = pd.read_csv('historical_stock_data.csv')\n\n# Remove "
        "unnecessary columns\ndata = data.drop(['symbol', 'date'], "
        "axis=1)\n\n# Handle missing values\ndata = data.fillna("
        "method='ffill')\n\n# Normalize the data\nscaler = "
        "MinMaxScaler()\ndata = scaler.fit_transform(data)\n\n# "
        "Split the data into training and testing sets\nX_train, "
        "X_test, y_train, y_test = train_test_split(data[:, :-1], "
        "data[:, -1], test_size=0.2, random_state=42)\n```\n\nNext "
        "request."
    )
    gt = (
        "Solution: To preprocess the historical stock data, we "
        "can perform the following steps:\n\n1. Remove any unnecessary"
        " columns that do not contribute to the prediction, such as"
        " the stock symbol or date.\n2. Check for and handle any missing"
        " or null values in the data.\n3. Normalize the data to ensure"
        " that all features are on the same scale. This can be done"
        " using techniques such as Min-Max scaling or Z-score"
        " normalization.\n4. Split the data into training and testing"
        " sets. The training set will be used to train the machine"
        " learning model, while the testing set will be used to"
        " evaluate its performance.\n\nHere is an example code snippet"
        " to preprocess the data using Pandas:\n\n\n```import pandas"
        " as pd```\n```from sklearn.preprocessing import MinMaxScaler"
        "```\n```from sklearn.model_selection import train_test_split"
        "```\n\n```# Read in the historical stock data```\n```data ="
        " pd.read_csv('historical_stock_data.csv')```\n\n```# Remove"
        " unnecessary columns```\n```data = data.drop(['symbol', "
        "'date'], axis=1)```\n\n```# Handle missing values```\n```data"
        " = data.fillna(method='ffill')```\n\n```# Normalize the data"
        "```\n```scaler = MinMaxScaler()```\n```data = scaler."
        "fit_transform(data)```\n\n```# Split the data into training"
        " and testing sets```\n```X_train, X_test, y_train, y_test"
        " = train_test_split(data[:, :-1], data[:, -1], test_size=0.2,"
        " random_state=42)```\n\n\nNext request."
    )

    out = text_utils.split_markdown_code(inp)
    assert out == gt


def test_split_markdown_code_br():
    inp = (
        "Solution: Define the Bayesian optimization object."
        "\n"
        "We can define the Bayesian optimization object using"
        " the BayesianOptimization class from the bayes_opt module."
        " Here is an example of how to define the Bayesian"
        " optimization object:"
        "\n"
        "```<br># Replace 'objective_function' with the actual"
        " objective function<br># Replace 'bounds' with the actual"
        " search space<br># Replace 'model' with the actual machine"
        " learning model<br>bo = BayesianOptimization(<br> "
        "f=objective_function,<br> pbounds=bounds,<br> verbose=2,<br>"
        " random_state=1,<br>)<br>```"
        "\n"
        "This will define the Bayesian optimization object with the"
        " specified objective function, search space, and machine"
        " learning model. The BayesianOptimization class takes "
        "several arguments, including f for the objective function,"
        " pbounds for the search space, verbose for the verbosity"
        " level, and random_state for the random seed."
        "\n"
        "Next request."
    )
    gt = (
        "Solution: Define the Bayesian optimization object."
        "\n"
        "We can define the Bayesian optimization object using the"
        " BayesianOptimization class from the bayes_opt module. Here is"
        " an example of how to define the Bayesian optimization object:"
        "\n"
        "\n```# Replace 'objective_function' with the actual objective"
        " function```\n```# Replace 'bounds' with the actual search"
        " space```\n```# Replace 'model' with the actual machine"
        " learning model```\n```bo = BayesianOptimization(```\n```"
        " f=objective_function,```\n``` pbounds=bounds,```\n``` "
        "verbose=2,```\n``` random_state=1,```\n```)```\n"
        "\n"
        "This will define the Bayesian optimization object with "
        "the specified objective function, search space, and machine"
        " learning model. The BayesianOptimization class takes several"
        " arguments, including f for the objective function, pbounds"
        " for the search space, verbose for the verbosity level, and"
        " random_state for the random seed."
        "\n"
        "Next request."
    )

    out = text_utils.split_markdown_code(inp)
    assert out == gt
