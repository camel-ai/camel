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
import argparse
import json
import logging
import os
import sys  # Import the sys module
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, List

app = None
products: List[Dict[str, Any]] = []
products_by_id: Dict[int, Dict[str, Any]] = {}
cart: List[Dict[str, Any]] = []
ACTION_COUNT: int = 0


def load_products(file_path: str = 'products.json') -> None:
    global products, products_by_id
    try:
        # The products.json is expected to be
        # in the same directory as this app.py
        # or given by mock_web.py
        script_dir = os.path.dirname(__file__)
        abs_file_path = os.path.join(script_dir, file_path)
        with open(abs_file_path, 'r') as f:
            products = json.load(f)
        products_by_id = {product['id']: product for product in products}
    except FileNotFoundError:
        sys.stderr.write(f"Error: {file_path} not found.\n")
        products = []
        products_by_id = {}
    except json.JSONDecodeError:
        sys.stderr.write(f"Error: Could not decode JSON from {file_path}.\n")
        products = []
        products_by_id = {}


# --- Logging Setup ---
def setup_logging(application):
    log_formatter = logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    )
    # Log to a file in the same directory as this script
    script_dir = os.path.dirname(__file__)
    log_file = os.path.join(script_dir, 'app.log')

    # File Handler
    file_handler = RotatingFileHandler(
        log_file, maxBytes=1024 * 1024 * 10, backupCount=5
    )  # 10MB per file, 5 backups
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.INFO)

    # Stream Handler (for console output)
    stream_handler = logging.StreamHandler(
        sys.stdout
    )  # Explicitly set to stdout
    stream_handler.setFormatter(log_formatter)
    stream_handler.setLevel(logging.INFO)

    application.logger.addHandler(file_handler)
    application.logger.addHandler(stream_handler)
    application.logger.setLevel(logging.INFO)
    application.logger.info(
        f"Logging setup complete. Logs will be saved to {log_file}"
    )


# --- End Logging Setup ---


# --- Task Mode Helper ---
def check_task_completion(current_cart_raw, ground_truth_spec):
    if not ground_truth_spec:  # No ground truth defined
        return False

    # Group current cart by product ID and count quantity
    current_cart_grouped = {}
    for item in current_cart_raw:
        pid = item['id']
        current_cart_grouped[pid] = current_cart_grouped.get(pid, 0) + 1

    # Convert ground truth spec to a comparable dictionary {product_id:
    # quantity}
    ground_truth_dict = {}
    for item_spec in ground_truth_spec:
        ground_truth_dict[item_spec['id']] = item_spec['quantity']

    # Check if current cart exactly matches ground truth
    # 1. Same number of unique product types
    if len(current_cart_grouped) != len(ground_truth_dict):
        return False

    # 2. Each product in current cart matches ground truth quantity, and all
    # ground truth items are present
    for pid, qty_spec in ground_truth_dict.items():
        if (
            pid not in current_cart_grouped
            or current_cart_grouped[pid] != qty_spec
        ):
            return False

    # Ensure no extra items in current_cart_grouped that are not in
    # ground_truth_dict (already covered by length check if all ground truth
    # items are found)
    # For robustness, explicitly check this too:
    for pid_current in current_cart_grouped.keys():
        if pid_current not in ground_truth_dict:
            return False

    return True


# --- End Task Mode Helper ---


# --- Task Completion Helper ---
def _trigger_task_completion_check():
    r"""Checks for task completion if in task mode and not already signaled."""
    # Uses global `app` and `cart`
    if app.config.get('TASK_ACTIVE') and not app.config.get(
        'TASK_COMPLETION_SIGNALED'
    ):
        if check_task_completion(cart, app.config.get('GROUND_TRUTH_CART')):
            app.config['TASK_COMPLETION_SIGNALED'] = True
            app.logger.info(
                "TASK COMPLETED: Ground truth cart state achieved."
            )


# --- End Task Completion Helper ---
def create_app():
    global app
    try:
        from flask import Flask, jsonify, render_template, request
    except ImportError:
        raise ImportError(
            "Flask not installed. Please install it with `pip install Flask`"
        )

    # Adjust template and static folder paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    app = Flask(
        __name__,
        template_folder=os.path.join(script_dir, 'templates'),
        static_folder=os.path.join(script_dir, 'static'),
    )
    setup_logging(app)

    # --- Global Task Config ---
    app.config['TASK_ACTIVE'] = False
    app.config['GROUND_TRUTH_CART'] = []
    app.config['TASK_COMPLETION_SIGNALED'] = False

    @app.route('/')
    def home():
        global ACTION_COUNT
        ACTION_COUNT += 1
        unique_categories = sorted({p["category"] for p in products})
        products_by_category = {}
        for product in products:
            category = product["category"]
            if category not in products_by_category:
                products_by_category[category] = []
            products_by_category[category].append(product)

        app.logger.info(
            "Home page requested. "
            f"Categories: {unique_categories}. Cart count: {len(cart)}"
        )
        # Pass products_by_category to the template instead of the flat
        # products list for main display
        return render_template(
            'index.html',
            products_by_category=products_by_category,
            categories=unique_categories,
            cart_count=len(cart),
            all_products=products,
        )

    @app.route('/product/<int:product_id>')
    def product_detail(product_id):
        global ACTION_COUNT
        ACTION_COUNT += 1
        product = products_by_id.get(product_id)
        app.logger.info(
            f"Product detail page requested for ID: {product_id}. "
            f"Cart count: {len(cart)}"
        )
        if product:
            return render_template(
                'product-detail.html', product=product, cart_count=len(cart)
            )
        return "Product not found", 404

    @app.route('/cart')
    def view_cart():
        global ACTION_COUNT
        ACTION_COUNT += 1
        total_price = sum(
            item['price'] * item.get('quantity', 1) for item in cart
        )
        app.logger.info(f"Cart page requested. Cart count: {len(cart)}")
        return render_template(
            'cart.html', cart_items=cart, total_price=total_price
        )

    @app.route('/api/products')
    def get_products():
        return jsonify(products)

    @app.route('/api/cart', methods=['GET'])
    def get_cart_api():
        total_price = sum(
            item['price'] * item.get('quantity', 1) for item in cart
        )
        return jsonify({'cart': cart, 'total_price': total_price})

    @app.route('/api/cart/add', methods=['POST'])
    def add_to_cart_api():
        global ACTION_COUNT
        data = request.json
        product_id = data.get('productId')

        if not product_id:
            return jsonify(
                {'success': False, 'message': 'Product ID is required'}
            ), 400

        product = products_by_id.get(product_id)
        if not product:
            return jsonify(
                {'success': False, 'message': 'Product not found'}
            ), 404

        # Check if product is already in cart
        for item in cart:
            if item['id'] == product_id:
                # If yes, just increment quantity
                item.get('quantity', 1)
                item['quantity'] = item.get('quantity', 1) + 1
                app.logger.info(
                    f"Incremented quantity for product {product_id} in cart."
                )
                return jsonify(
                    {'success': True, 'cart': cart, 'cart_count': len(cart)}
                )

        # If not, add new item to cart
        cart_item = product.copy()
        cart_item['quantity'] = 1  # Start with quantity 1
        cart.append(cart_item)
        ACTION_COUNT += 1  # Increment on successful add

        _trigger_task_completion_check()

        app.logger.info(f"Added product {product_id} to cart.")
        return jsonify(
            {'success': True, 'cart': cart, 'cart_count': len(cart)}
        )

    @app.route('/api/cart/update', methods=['POST'])
    def update_cart_item_api():
        data = request.json
        product_id = data.get('productId')
        quantity = data.get('quantity')

        if not product_id:
            return jsonify(
                {'success': False, 'message': 'Product ID is required'}
            ), 400

        try:
            # Ensure quantity is a non-negative integer
            quantity = int(quantity)
            if quantity < 0:
                raise ValueError
        except (ValueError, TypeError):
            return jsonify(
                {'success': False, 'message': 'Invalid quantity'}
            ), 400

        found_item = False
        for item in cart:
            if item['id'] == product_id:
                if quantity > 0:
                    item['quantity'] = quantity
                    app.logger.info(
                        "Updated quantity for product "
                        f"{product_id} to {quantity}."
                    )
                else:
                    # If quantity is 0, remove the item
                    cart.remove(item)
                    app.logger.info(f"Removed product {product_id} from cart.")
                found_item = True
                break

        if not found_item:
            return jsonify(
                {'success': False, 'message': 'Product not in cart'}
            ), 404

        _trigger_task_completion_check()

        total_price = sum(
            item['price'] * item.get('quantity', 1) for item in cart
        )
        return jsonify(
            {
                'success': True,
                'cart': cart,
                'cart_count': len(cart),
                'total_price': total_price,
            }
        )

    @app.route('/api/cart/remove', methods=['POST'])
    def remove_from_cart_api():
        global cart, ACTION_COUNT
        data = request.json
        product_id = data.get('productId')

        if not product_id:
            return jsonify(
                {'success': False, 'message': 'Product ID is required'}
            ), 400

        original_cart_len = len(cart)
        # List comprehension to create a new list excluding the item to be
        # removed This is simpler than finding index and deleting
        cart[:] = [item for item in cart if item['id'] != product_id]

        if len(cart) < original_cart_len:
            ACTION_COUNT += 1  # Increment on successful remove
            app.logger.info(f"Removed product {product_id} from cart.")

            _trigger_task_completion_check()

            total_price = sum(
                item['price'] * item.get('quantity', 1) for item in cart
            )
            return jsonify(
                {
                    'success': True,
                    'cart': cart,
                    'cart_count': len(cart),
                    'total_price': total_price,
                }
            )

        return jsonify(
            {'success': False, 'message': 'Product not in cart'}
        ), 404

    @app.route('/task/start', methods=['POST'])
    def start_task():
        global cart, ACTION_COUNT
        ACTION_COUNT = 0  # Reset action counter
        data = request.json
        ground_truth = data.get('ground_truth_cart')

        if not isinstance(ground_truth, list):
            return jsonify(
                {
                    'success': False,
                    'message': '`ground_truth_cart` must be a list.',
                }
            ), 400

        # Validate ground truth spec
        for item_spec in ground_truth:
            if not all(k in item_spec for k in ['id', 'quantity']):
                return jsonify(
                    {
                        'success': False,
                        'message': (
                            'Each item in `ground_truth_cart` must have '
                            '`id` and `quantity`.'
                        ),
                    }
                ), 400

        app.config['TASK_ACTIVE'] = True
        app.config['GROUND_TRUTH_CART'] = ground_truth
        app.config['TASK_COMPLETION_SIGNALED'] = False  # Reset signal
        cart = []  # Reset cart
        app.logger.info(f"TASK MODE STARTED. Ground truth: {ground_truth}")
        return jsonify(
            {'success': True, 'message': 'Task mode started. Cart reset.'}
        )

    @app.route('/task/check', methods=['GET'])
    def check_task():
        global ACTION_COUNT
        if not app.config.get('TASK_ACTIVE'):
            return jsonify(
                {'success': False, 'message': 'Task mode is not active.'}
            ), 400

        completed = app.config.get('TASK_COMPLETION_SIGNALED', False)
        if completed:
            message = "Task completed successfully."
        else:
            message = "Task not yet completed."

        return jsonify(
            {
                'success': True,
                'completed': completed,
                'steps': ACTION_COUNT,
                'message': message,
            }
        )

    @app.route('/task/stop', methods=['POST'])
    def stop_task():
        global cart
        app.config['TASK_ACTIVE'] = False
        app.config['GROUND_TRUTH_CART'] = []
        app.config['TASK_COMPLETION_SIGNALED'] = False
        cart = []  # Reset cart
        app.logger.info("TASK MODE STOPPED. Cart reset.")
        return jsonify(
            {'success': True, 'message': 'Task mode stopped. Cart reset.'}
        )

    return app


def main():
    parser = argparse.ArgumentParser(
        description="Run the mock website server."
    )
    parser.add_argument(
        '--port', type=int, default=5000, help='Port to run the server on.'
    )
    args = parser.parse_args()

    # Load products specific to this app
    load_products()
    flask_app = create_app()

    if flask_app:
        # Use 0.0.0.0 to make it accessible from the dispatcher
        # Disable the reloader to prevent state loss on logging
        flask_app.run(
            debug=True, port=args.port, host='0.0.0.0', use_reloader=False
        )


if __name__ == "__main__":
    main()
