# Amazon Page Template for Web Agent Testing

This project is an Amazon-like page template designed to test and demonstrate web agent operations. It features a Flask backend and a dynamic frontend, allowing for simulation of product browsing, searching, and shopping cart interactions.

## Features

*   **Product Display:** View a list of products with images, descriptions, ratings, and prices.
*   **Product Detail Pages:** Click on a product to see its dedicated detail page.
*   **Dynamic Categories:** Product categories are dynamically populated in the search filter.
*   **Search Functionality:** Filter products by name and category.
*   **Shopping Cart:**
    *   Add products to the cart from product detail pages.
    *   View and manage cart contents (update quantities, remove items).
    *   Real-time cart count update in the header.
*   **Flask Backend:** Manages product data, cart logic, and serves pages/API endpoints.
*   **Logging:** Detailed logging of backend operations, saved to `app.log`. Includes information on page requests, API calls, and cart modifications.
*   **Task Mode (Optional):**
    *   Allows the application to be started with a specific shopping cart configuration as a "ground truth" target.
    *   When the cart contents exactly match the ground truth, a "Task Complete!" alert is triggered on the frontend, and a special message is logged on the backend.
    *   This mode is useful for testing web agents designed to achieve specific goals within the e-commerce environment.

## Setup and Usage

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    The `requirements.txt` file should primarily contain:
    ```
    Flask>=2.0
    ```

2.  **Create Product Image Directory:**
    Ensure you have an `assets/img/products/` directory inside the `static` folder (`static/assets/img/products/`). Place your product images (e.g., `laptop.jpg`, `mouse.jpg`) here. The sample product data in `app.py` references these paths.

3.  **Running the Application:**

    *   **Normal Mode:**
        ```bash
        python app.py
        ```
        The application will be accessible at `http://127.0.0.1:5000/`.

    *   **Task Mode:**
        To run in task mode, use the `--task-mode` flag and provide a `--ground-truth` JSON string.
        ```bash
        python app.py --task-mode --ground-truth "[{\"id\": 1, \"quantity\": 2}, {\"id\": 3, \"quantity\": 1}]"
        ```
        *   Replace the JSON string with your desired target cart configuration.
        *   The JSON string needs to be properly escaped for the command line.
        *   **Example Ground Truths:**
            *   `"[{\"id\": 1, \"quantity\": 1}]"` (One of product ID 1)
            *   `"[]"` (Empty cart)

        Logs, including task completion, will be saved to `app.log`.

## Project Structure

```
.amazon-website-template-main/
├── app.py                     # Main Flask application, routes, API logic
├── requirements.txt           # Python dependencies
├── static/
│   └── assets/
│       ├── img/                 # Images (logo, product placeholders, etc.)
│       │   └── products/      # Product images
│       ├── js/                  # JavaScript files
│       │   ├── script.js        # Main page interactions, search
│       │   ├── product-detail.js # Product detail page logic
│       │   └── cart-page.js     # Shopping cart page logic
│       └── style/               # CSS files
│           ├── global.css
│           └── local.css
├── templates/
│   ├── index.html             # Homepage template
│   ├── product-detail.html    # Product detail page template
│   └── cart.html              # Shopping cart page template
├── app.log                    # Log file (generated at runtime)
└── README.md                  # This file
```

## TODO: Automated Question Generation Module

A planned future module for this project is the development of an automated question generation system. This system would analyze the current state of the web application environment (e.g., visible elements, available products, cart status) and generate relevant questions or tasks for a web agent to solve. 

This could involve:
*   Identifying interactable elements and their states.
*   Understanding the current context (e.g., on product page, in cart).
*   Formulating natural language questions or goal descriptions based on this context (e.g., "Find a product under $50 in the Electronics category and add it to the cart," or "What is the current subtotal of the cart after adding two units of item X?").


