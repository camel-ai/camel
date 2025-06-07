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
from logging.handlers import RotatingFileHandler

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# --- Global Task Config ---
app.config['TASK_ACTIVE'] = False
app.config['GROUND_TRUTH_CART'] = []
app.config['TASK_COMPLETION_SIGNALED'] = False


# --- End Global Task Config ---


# --- Logging Setup ---
def setup_logging(application):
    # Remove default Flask handler if it exists
    # for handler in application.logger.handlers[:]:
    #     application.logger.removeHandler(handler)

    log_formatter = logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    )
    log_file = 'app.log'

    # File Handler
    file_handler = RotatingFileHandler(
        log_file, maxBytes=1024 * 1024 * 10, backupCount=5
    )  # 10MB per file, 5 backups
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.INFO)

    # Stream Handler (for console output)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(log_formatter)
    stream_handler.setLevel(logging.INFO)

    application.logger.addHandler(file_handler)
    application.logger.addHandler(stream_handler)
    application.logger.setLevel(logging.INFO)
    application.logger.info(
        "Logging setup complete. Logs will be saved to app.log"
    )


setup_logging(app)


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

# Sample product data (can be moved to a database later)
products = [
    {
        "id": 1,
        "name": "Gaming Laptop",
        "price": 1200,
        "image": "assets/img/products/laptop.jpg",
        "category": "Electronics",
        "rating": 4.5,
        "description": "High-performance gaming laptop with latest specs.",
    },
    {
        "id": 2,
        "name": "Wireless Mouse",
        "price": 25,
        "image": "assets/img/products/mouse.jpg",
        "category": "Electronics",
        "rating": 4.0,
        "description": "Ergonomic wireless mouse with long battery life.",
    },
    {
        "id": 3,
        "name": "Mechanical Keyboard",
        "price": 75,
        "image": "assets/img/products/keyboard.jpg",
        "category": "Electronics",
        "rating": 4.8,
        "description": "RGB mechanical keyboard with customizable keys.",
    },
    {
        "id": 4,
        "name": "Coffee Maker",
        "price": 50,
        "image": "assets/img/products/coffeemaker.jpg",
        "category": "Home Goods",
        "rating": 3.9,
        "description": "Drip coffee maker with programmable timer.",
    },
    {
        "id": 5,
        "name": "Bluetooth Speaker",
        "price": 45,
        "image": "assets/img/products/speaker.jpg",
        "category": "Electronics",
        "rating": 4.2,
        "description": "Portable Bluetooth speaker with rich sound.",
    },
]
products += [
    {
        "id": 6,
        "name": "Smartphone",
        "price": 699,
        "image": "assets/img/products/smartphone.jpg",
        "category": "Electronics",
        "rating": 4.6,
        "description": "Latest-gen smartphone with stunning display and fast "
                       "performance.",
    },
    {
        "id": 7,
        "name": "Air Purifier",
        "price": 130,
        "image": "assets/img/products/airpurifier.jpg",
        "category": "Home Goods",
        "rating": 4.3,
        "description": "HEPA air purifier with quiet operation and multiple "
                       "fan speeds.",
    },
    {
        "id": 8,
        "name": "Fitness Tracker",
        "price": 85,
        "image": "assets/img/products/fitnesstracker.jpg",
        "category": "Electronics",
        "rating": 4.1,
        "description": "Waterproof fitness tracker with heart rate and sleep"
                       " monitoring.",
    },
    {
        "id": 9,
        "name": "Electric Kettle",
        "price": 35,
        "image": "assets/img/products/kettle.jpg",
        "category": "Home Goods",
        "rating": 4.0,
        "description": "Stainless steel electric kettle with auto shut-off "
                       "feature.",
    },
    {
        "id": 10,
        "name": "Noise Cancelling Headphones",
        "price": 150,
        "image": "assets/img/products/headphones.jpg",
        "category": "Electronics",
        "rating": 4.7,
        "description": "Over-ear headphones with active noise cancellation "
                       "and long battery life.",
    },
]

cart = []  # In-memory cart, ideally this would be session-based or
# database-driven


@app.route('/')
def home():
    unique_categories = sorted(list(set(p["category"] for p in products)))

    products_by_category = {}
    for product in products:
        category = product["category"]
        if category not in products_by_category:
            products_by_category[category] = []
        products_by_category[category].append(product)

    app.logger.info(
        f"Home page requested. Categories: {unique_categories}. Cart count: "
        f"{len(cart)}"
    )
    # Pass products_by_category to the template instead of the flat products
    # list for main display
    return render_template(
        'index.html',
        products_by_category=products_by_category,
        categories=unique_categories,
        cart_count=len(cart),
        all_products=products,
    )


@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = next((p for p in products if p['id'] == product_id), None)
    app.logger.info(
        f"Product detail page requested for ID: {product_id}. Cart count: "
        f"{len(cart)}"
    )
    if product:
        app.logger.info(f"Product found: {product['name']}")
        return render_template(
            'product-detail.html', product=product, cart_count=len(cart)
        )
    app.logger.info(f"Product ID {product_id} not found.")
    return "Product not found", 404


@app.route('/cart')
def view_cart():
    app.logger.info(
        f"Cart page requested. Current raw cart item count: {len(cart)}"
    )
    # Group cart items for display
    grouped_cart = {}
    for item in cart:
        if item['id'] in grouped_cart:
            grouped_cart[item['id']]['quantity'] += 1
        else:
            grouped_cart[item['id']] = {**item, 'quantity': 1}

    cart_items_for_template = list(grouped_cart.values())
    app.logger.info(
        f"Grouped cart for display: {len(cart_items_for_template)} unique "
        f"items. Data: {cart_items_for_template}"
    )
    return render_template(
        'cart.html', cart_items=cart_items_for_template, cart_count=len(cart)
    )


@app.route('/api/products')
def get_products():
    app.logger.info(
        f"API: Products requested. Returning {len(products)} products."
    )
    return jsonify(products)


@app.route('/api/cart', methods=['GET'])
def get_cart_api():
    app.logger.info(
        f"API: Cart data requested. Returning {len(cart)} raw cart items. "
        f"Cart: {cart}"
    )
    return jsonify(cart)


@app.route('/api/cart/add', methods=['POST'])
def add_to_cart_api():
    data = request.json
    product_id = data.get('productId')
    quantity = data.get('quantity', 1)
    app.logger.info(
        f"API: Add to cart request received. Product ID: {product_id}, "
        f"Quantity: {quantity}"
    )

    product_to_add = next((p for p in products if p['id'] == product_id), None)

    if product_to_add:
        for _ in range(quantity):
            cart.append(product_to_add)
        app.logger.info(
            f"Product '{product_to_add['name']}' (ID: {product_id}) added to "
            f"cart. Quantity: {quantity}. New cart count: {len(cart)}. "
            f"Current cart: {cart}"
        )

        response_data = {
            'success': True,
            'cart_count': len(cart),
            'message': 'Product added to cart',
        }
        if (
                app.config['TASK_ACTIVE']
                and not app.config['TASK_COMPLETION_SIGNALED']
        ):
            if check_task_completion(cart, app.config['GROUND_TRUTH_CART']):
                app.logger.info(
                    "TASK COMPLETED: Ground truth met after adding to cart."
                )
                response_data['task_completed'] = True
                app.config['TASK_COMPLETION_SIGNALED'] = True
        return jsonify(response_data), 200
    app.logger.warning(
        f"API: Add to cart failed. Product ID {product_id} not found."
    )
    return jsonify({'success': False, 'message': 'Product not found'}), 404


@app.route('/api/cart/update', methods=['POST'])
def update_cart_item_api():
    global cart
    data = request.json
    product_id = data.get('productId')
    new_quantity = data.get(
        'quantity'
    )  # Assuming quantity is the new total quantity
    app.logger.info(
        f"API: Update cart request received. Product ID: {product_id}, "
        f"New Quantity: {new_quantity}"
    )

    if new_quantity is None or new_quantity < 0:
        app.logger.warning(
            f"API: Update cart failed for Product ID {product_id}. Invalid "
            f"quantity: {new_quantity}."
        )
        return jsonify({'success': False, 'message': 'Invalid quantity'}), 400

    # Find the product details
    product_to_update_details = next(
        (p for p in products if p['id'] == product_id), None
    )
    if not product_to_update_details:
        app.logger.warning(
            f"API: Update cart failed. Product ID {product_id} not found in "
            f"products list."
        )
        return jsonify(
            {'success': False, 'message': 'Product details not found'}
        ), 404

    # Rebuild the cart: remove all existing instances of this product,
    # then add back with new quantity
    temp_cart = [item for item in cart if item['id'] != product_id]

    for _ in range(new_quantity):
        temp_cart.append(product_to_update_details)

    cart = temp_cart
    app.logger.info(
        f"Cart updated for Product ID {product_id}. Product: '"
        f"{product_to_update_details['name']}'. New quantity: "
        f"{new_quantity}. New cart count: {len(cart)}. Current cart: {cart}"
    )

    response_data = {'success': True, 'cart_count': len(cart)}
    if (
            app.config['TASK_ACTIVE']
            and not app.config['TASK_COMPLETION_SIGNALED']
    ):
        if check_task_completion(cart, app.config['GROUND_TRUTH_CART']):
            app.logger.info(
                "TASK COMPLETED: Ground truth met after updating cart."
            )
            response_data['task_completed'] = True
            app.config['TASK_COMPLETION_SIGNALED'] = True
    return jsonify(response_data), 200


@app.route('/api/cart/remove', methods=['POST'])
def remove_from_cart_api():
    data = request.json
    product_id = data.get('productId')
    app.logger.info(
        f"API: Remove from cart request received. Product ID: {product_id}"
    )

    global cart
    original_length = len(cart)
    product_removed_details = next(
        (item for item in cart if item['id'] == product_id), None
    )

    cart = [item for item in cart if item['id'] != product_id]
    items_removed_count = original_length - len(cart)

    if items_removed_count > 0 and product_removed_details:
        app.logger.info(
            f"Product '{product_removed_details['name']}' (ID: {product_id}) "
            f"removed from cart. Items removed: {items_removed_count}. New "
            f"cart count: {len(cart)}. Current cart: {cart}"
        )

        response_data = {'success': True, 'cart_count': len(cart)}
        if (
                app.config['TASK_ACTIVE']
                and not app.config['TASK_COMPLETION_SIGNALED']
        ):
            # Check completion even on removal, as target might be an empty
            # cart or fewer items
            if check_task_completion(cart, app.config['GROUND_TRUTH_CART']):
                app.logger.info(
                    "TASK COMPLETED: Ground truth met after removing from "
                    "cart."
                )
                response_data['task_completed'] = True
                app.config['TASK_COMPLETION_SIGNALED'] = True
        return jsonify(response_data), 200
    elif items_removed_count == 0:
        app.logger.warning(
            f"API: Remove from cart failed. Product ID {product_id} not "
            f"found in cart."
        )
        return jsonify(
            {'success': False, 'message': 'Product not found in cart'}
        ), 404
    else:  # Should not happen if logic is correct
        app.logger.error(
            f"API: Remove from cart unusual state for Product ID "
            f"{product_id}. Items removed: {items_removed_count}."
        )
        return jsonify(
            {'success': False, 'message': 'Error removing product from cart'}
        ), 500


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Flask E-commerce App with Optional Task Mode'
    )
    parser.add_argument(
        '--task-mode', action='store_true', help='Enable task mode.'
    )
    parser.add_argument(
        '--ground-truth',
        type=str,
        help='JSON string for ground truth cart. E.g., \'[{"id": 1, '
             '"quantity": 1}]\'',
    )
    args = parser.parse_args()

    if args.task_mode:
        if args.ground_truth:
            try:
                ground_truth_list = json.loads(args.ground_truth)
                # Validate ground_truth_list structure (basic check)
                if not isinstance(ground_truth_list, list) or not all(
                        isinstance(item, dict)
                        and 'id' in item
                        and 'quantity' in item
                        for item in ground_truth_list
                ):
                    raise ValueError(
                        "Ground truth must be a list of dicts with 'id' and "
                        "'quantity'."
                    )

                app.config['TASK_ACTIVE'] = True
                app.config['GROUND_TRUTH_CART'] = ground_truth_list
                app.logger.info(
                    f"Application starting in TASK MODE. Ground Truth: "
                    f"{app.config['GROUND_TRUTH_CART']}"
                )
            except json.JSONDecodeError:
                app.logger.error(
                    "Invalid JSON string for --ground-truth. Starting in "
                    "normal mode."
                )
            except ValueError as ve:
                app.logger.error(
                    f"Error in ground truth format: {ve}. Starting in normal "
                    f"mode."
                )
        else:
            app.logger.warning(
                "--task-mode enabled but --ground-truth not provided. "
                "Starting in normal mode."
            )
    else:
        app.logger.info("Application starting in NORMAL MODE.")

    # setup_logging(app) # Already called above
    app.logger.info("Starting Flask application...")
    app.run(debug=True)
