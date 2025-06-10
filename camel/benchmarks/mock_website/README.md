# Mock Website Benchmarks for Web Agent Testing

This project provides a framework for testing web agents against various mock websites. It features a central dispatcher (`mock_web.py`) that manages different test environments, each simulating a specific type of website (e.g., an e-commerce site). The initial example project is an Amazon-like shopping website.

## Core Concepts

*   **Dispatcher (`mock_web.py`):** The single entry point for running any benchmark. It handles:
    *   Downloading necessary web assets (HTML templates, CSS, JS) for a specific project from Hugging Face (https://huggingface.co/datasets/camel-ai/mock_websites).
    *   Reading the task configuration from `task.json`.
    *   Launching the project's dedicated Flask web server as a background process.
    *   Monitoring the server for task completion via API polling.
    *   Reporting the final results (success status, number of operations) and shutting down the server.
*   **Projects (e.g., `shopping_mall/`):** Each project is a self-contained Flask application representing a unique website.
*   **Task Configuration (`task.json`):** A central JSON file that defines the environment and the goal for the agent.

## Example Project: `shopping_mall`

The included `shopping_mall` project simulates an e-commerce website with the following features:
*   **Product Display:** View a list of products with images, descriptions, ratings, and prices.
*   **Product Detail Pages:** Click on a product to see its dedicated detail page.
*   **Shopping Cart:** Add products, view the cart, and manage its contents.
*   **API-Driven:** The backend provides API endpoints for all state-changing actions.

## Setup and Usage

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    This will install `Flask`, `huggingface-hub`, `requests`, and other necessary packages.

2.  **Configure the Task:**
    Edit the `task.json` file to define the products available on the website and the agent's goal. The structure is as follows:
    ```json
    {
        "products": [
            {
                "id": 1,
                "name": "Gaming Laptop",
                "price": 1200,
                "image": "assets/img/products/laptop.jpg",
                "category": "Electronics",
                "rating": 4.5,
                "description": "High-performance gaming laptop with latest specs."
            }
        ],
        "ground_truth_cart": [
            {
                "id": 1,
                "quantity": 1
            }
        ]
    }
    ```
    *   `products`: A list of all product objects available in the environment.
    *   `ground_truth_cart`: A list of items that defines the target state of the shopping cart for the task to be considered complete.

3.  **Running the Benchmark:**
    Use the `mock_web.py` dispatcher to run a project.
    ```bash
    python mock_web.py --project shopping_mall
    ```
    *   `--project`: Specifies which mock website project to run (default: `shopping_mall`).
    *   `--port`: Specifies the port to run the server on (default: `5001`).

    The dispatcher will start the server and begin polling for task completion. You or your agent can then interact with the website at `http://127.0.0.1:5001/`. Once the conditions defined in `ground_truth_cart` are met, the dispatcher will automatically detect it, report the results, and shut down. You can also stop it early by pressing `Ctrl+C`.

## Logging

*   `dispatcher.log`: High-level log from the dispatcher, showing setup, status, and final results.
*   `shopping_mall/app.log`: Detailed internal log from the Flask application for the `shopping_mall` project.

## Project Structure

```
.
├── mock_web.py                # Main dispatcher for running benchmarks
├── task.json                  # Task configuration file
├── requirements.txt           # Python dependencies
├── shopping_mall/             # Example project: shopping_mall
│   └── app.py                 # Flask application for this project
├── dispatcher.log             # (Generated at runtime)
└── README.md                  # This file
```
The dispatcher will automatically download project-specific `templates` and `static` folders from Hugging Face Hub and place them inside the corresponding project directory at runtime.

## TODO: Automated Question Generation Module

A planned future module for this project is the development of an automated question generation system. This system would analyze the current state of the web application environment (e.g., visible elements, available products, cart status) and generate relevant questions or tasks for a web agent to solve. 

This could involve:
*   Identifying interactable elements and their states.
*   Understanding the current context (e.g., on product page, in cart).
*   Formulating natural language questions or goal descriptions based on this context (e.g., "Find a product under $50 in the Electronics category and add it to the cart," or "What is the current subtotal of the cart after adding two units of item X?").


