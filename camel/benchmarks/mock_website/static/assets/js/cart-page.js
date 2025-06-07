document.addEventListener('DOMContentLoaded', () => {
    const cartItemsContainer = document.getElementById('cart-items-container');
    const cartSummaryContainer = document.getElementById('cart-summary');
    const cartCountElement = document.getElementById('c0'); // Header cart count
    const totalPriceElement = document.getElementById('total-price'); // Span for total price

    // Function to update header cart display count
    function updateHeaderCartCount(count) {
        if (cartCountElement) {
            cartCountElement.textContent = count;
        }
    }

    // Function to update total price display
    function updateTotalPriceDisplay(cart) {
        if (!totalPriceElement) return;
        let total = 0;
        cart.forEach(item => {
            // Ensure item.quantity is available from grouped cart data
            const productDetails = window.allProductsData.find(p => p.id === item.id); // Assuming window.allProductsData is available
            if(productDetails){
                total += productDetails.price * item.quantity; // item.quantity should be from the grouped cart from API
            }
        });
        totalPriceElement.textContent = total.toFixed(2);
    }

    async function renderCartItems() {
        try {
            const response = await fetch('/api/cart');
            if (!response.ok) throw new Error('Failed to fetch cart items');
            const currentCartRaw = await response.json(); // This is the raw cart (list of all items)
            
            updateHeaderCartCount(currentCartRaw.length);

            if (!cartItemsContainer) {
                console.error('Cart container not found.');
                return;
            }

            cartItemsContainer.innerHTML = '';
            if (cartSummaryContainer) cartSummaryContainer.innerHTML = '';

            if (currentCartRaw.length === 0) {
                cartItemsContainer.innerHTML = '<p class="col-12 text-center">Your cart is currently empty.</p>';
                 if (cartSummaryContainer) {
                    cartSummaryContainer.innerHTML = '<div class="col-12 text-end"><h4>Total: $0.00</h4></div>';
                }
                return;
            }

            // Group items by ID to count quantities for display
            const groupedCart = currentCartRaw.reduce((acc, product) => {
                acc[product.id] = acc[product.id] || { ...product, quantity: 0 };
                acc[product.id].quantity++;
                return acc;
            }, {});

            let calculatedTotalPrice = 0;

            Object.values(groupedCart).forEach(item => {
                const itemDiv = document.createElement('div');
                itemDiv.className = 'col-12 mb-3 border-bottom pb-3';
                // Use url_for for images, or ensure image paths from API are correct for static serving
                const imageUrl = `/static/${item.image}`;
                itemDiv.innerHTML = `
                    <div class="row align-items-center" data-item-id="${item.id}">
                        <div class="col-md-2">
                            <img src="${imageUrl}" alt="${item.name}" class="img-fluid" style="max-height: 100px; object-fit: contain;">
                        </div>
                        <div class="col-md-4">
                            <h5>${item.name}</h5>
                            <p>Price: $${item.price}</p>
                        </div>
                        <div class="col-md-3">
                            <label for="quantity-${item.id}">Quantity:</label>
                            <input type="number" id="quantity-${item.id}" class="form-control quantity-input" value="${item.quantity}" min="0" data-id="${item.id}" style="width: 70px;">
                        </div>
                        <div class="col-md-2">
                            <p>Subtotal: $${(item.price * item.quantity).toFixed(2)}</p>
                        </div>
                        <div class="col-md-1">
                            <button class="btn btn-danger btn-sm remove-item" data-id="${item.id}"><i class="bi bi-trash"></i></button>
                        </div>
                    </div>
                `;
                cartItemsContainer.appendChild(itemDiv);
                calculatedTotalPrice += item.price * item.quantity;
            });

            if (cartSummaryContainer) {
                cartSummaryContainer.innerHTML = `
                    <div class="col-12 text-end">
                        <h4>Total: $<span id="total-price">${calculatedTotalPrice.toFixed(2)}</span></h4>
                        <button class="btn btn-success">Proceed to Checkout</button>
                    </div>
                `;
            }
            
            addEventListenersToCartItems();

        } catch (error) {
            console.error("Error rendering cart items:", error);
            if (cartItemsContainer) cartItemsContainer.innerHTML = '<p class="text-center text-danger">Could not load cart. Please try again.</p>';
        }
    }

    function addEventListenersToCartItems() {
        document.querySelectorAll('.quantity-input').forEach(input => {
            input.addEventListener('change', handleUpdateQuantity);
        });
        document.querySelectorAll('.remove-item').forEach(button => {
            button.addEventListener('click', handleRemoveItem);
        });
    }

    async function handleUpdateQuantity(event) {
        const productId = parseInt(event.target.dataset.id);
        const newQuantity = parseInt(event.target.value);

        if (newQuantity < 0) { // Allow 0 to remove item effectively via quantity update
            event.target.value = 0; // or handle as remove
            // Consider calling removeItem if quantity is 0
        }

        try {
            const response = await fetch('/api/cart/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ productId: productId, quantity: newQuantity })
            });
            const result = await response.json();
            if (result.success) {
                renderCartItems(); // Re-render the cart to reflect changes and new totals
                updateHeaderCartCount(result.cart_count);
                if (result.task_completed) {
                    alert('Task Complete! Congratulations!');
                }
            } else {
                console.error("Failed to update quantity:", result.message);
                alert("Error: " + result.message); 
                // Optionally, revert input value or re-render to show server state
                renderCartItems(); // Re-render to be safe
            }
        } catch (error) {
            console.error("Error updating quantity:", error);
            alert("Error updating quantity. Please try again.");
            renderCartItems(); // Re-render to be safe
        }
    }

    async function handleRemoveItem(event) {
        const productId = parseInt(event.currentTarget.dataset.id);
        try {
            const response = await fetch('/api/cart/remove', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ productId: productId })
            });
            const result = await response.json();
            if (result.success) {
                renderCartItems(); // Re-render the cart
                updateHeaderCartCount(result.cart_count);
                if (result.task_completed) {
                    alert('Task Complete! Congratulations!');
                }
            } else {
                console.error("Failed to remove item:", result.message);
                alert("Error: " + result.message);
            }
        } catch (error) {
            console.error("Error removing item:", error);
            alert("Error removing item. Please try again.");
        }
    }

    // Initial render
    renderCartItems();
}); 