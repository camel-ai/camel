import re


def split_markdown_code(string: str) -> str:
    substr_list = string.split("```")
    out = []
    for i_subs, subs in enumerate(substr_list):
        if i_subs % 2 == 0:
            out.append(subs)
        else:  # inside code
            rx = r"\n+"
            repl = lambda m: "```{}```".format(m.group(0))
            new_subs = re.sub(rx, repl, subs)
            out.append(new_subs)
    out_str = "```".join(out)
    out_str_cleanup = re.sub(r"``````", "", out_str)
    return out_str_cleanup


if __name__ == "__main__":
    inp = "Solution: To preprocess the historical stock data, we can perform the following steps:\n\n1. Remove any unnecessary columns that do not contribute to the prediction, such as the stock symbol or date.\n2. Check for and handle any missing or null values in the data.\n3. Normalize the data to ensure that all features are on the same scale. This can be done using techniques such as Min-Max scaling or Z-score normalization.\n4. Split the data into training and testing sets. The training set will be used to train the machine learning model, while the testing set will be used to evaluate its performance.\n\nHere is an example code snippet to preprocess the data using Pandas:\n\n```\nimport pandas as pd\nfrom sklearn.preprocessing import MinMaxScaler\nfrom sklearn.model_selection import train_test_split\n\n# Read in the historical stock data\ndata = pd.read_csv('historical_stock_data.csv')\n\n# Remove unnecessary columns\ndata = data.drop(['symbol', 'date'], axis=1)\n\n# Handle missing values\ndata = data.fillna(method='ffill')\n\n# Normalize the data\nscaler = MinMaxScaler()\ndata = scaler.fit_transform(data)\n\n# Split the data into training and testing sets\nX_train, X_test, y_train, y_test = train_test_split(data[:, :-1], data[:, -1], test_size=0.2, random_state=42)\n```\n\nNext request."
    gt = "Solution: To preprocess the historical stock data, we can perform the following steps:\n\n1. Remove any unnecessary columns that do not contribute to the prediction, such as the stock symbol or date.\n2. Check for and handle any missing or null values in the data.\n3. Normalize the data to ensure that all features are on the same scale. This can be done using techniques such as Min-Max scaling or Z-score normalization.\n4. Split the data into training and testing sets. The training set will be used to train the machine learning model, while the testing set will be used to evaluate its performance.\n\nHere is an example code snippet to preprocess the data using Pandas:\n\n\n```import pandas as pd```\n```from sklearn.preprocessing import MinMaxScaler```\n```from sklearn.model_selection import train_test_split```\n\n```# Read in the historical stock data```\n```data = pd.read_csv('historical_stock_data.csv')```\n\n```# Remove unnecessary columns```\n```data = data.drop(['symbol', 'date'], axis=1)```\n\n```# Handle missing values```\n```data = data.fillna(method='ffill')```\n\n```# Normalize the data```\n```scaler = MinMaxScaler()```\n```data = scaler.fit_transform(data)```\n\n```# Split the data into training and testing sets```\n```X_train, X_test, y_train, y_test = train_test_split(data[:, :-1], data[:, -1], test_size=0.2, random_state=42)```\n\n\nNext request."

    out = split_markdown_code(inp)
    assert out == gt
    print("Test pass")
