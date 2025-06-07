document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    const productIdAttribute = document.getElementById('add-to-cart-detail')?.dataset.productId;
    // Product ID is now primarily taken from the data attribute set by Jinja
    const productId = productIdAttribute ? parseInt(productIdAttribute) : parseInt(params.get('id'));

    const container = document.getElementById('product-detail-container');
    const cartCountElement = document.getElementById('c0'); // Header cart count
    const addToCartButtonDetail = document.getElementById('add-to-cart-detail');
    const quantityInput = document.getElementById('quantity');

    // Product data is now rendered by Jinja in product-detail.html
    // This script mainly handles the "Add to Cart" button interaction

    // Function to update header cart display count (can be called after API success)
    function updateHeaderCartCount(count) {
        if (cartCountElement) {
            cartCountElement.textContent = count;
        }
    }
    
    // Fetch initial cart count to ensure header is up-to-date
    async function fetchInitialCartCount() {
        try {
            const response = await fetch('/api/cart');
            if (!response.ok) throw new Error('Failed to fetch cart count');
            const currentCart = await response.json();
            updateHeaderCartCount(currentCart.length);
        } catch (error) {
            console.error("Error fetching initial cart state:", error);
            updateHeaderCartCount(0); // Default to 0 on error
        }
    }

    if (addToCartButtonDetail && quantityInput) {
        addToCartButtonDetail.addEventListener('click', async () => {
            const quantity = parseInt(quantityInput.value);
            if (quantity > 0 && productId) {
                try {
                    const response = await fetch('/api/cart/add', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ productId: productId, quantity: quantity })
                    });
                    const result = await response.json();
                    if (result.success) {
                        updateHeaderCartCount(result.cart_count);
                        // Optionally, provide user feedback (e.g., a small message near the button)
                        console.log('Product(s) added to cart', result);
                        alert(`${quantity} item(s) added to cart!`); // Simple feedback
                        if (result.task_completed) {
                            alert('Task Complete! Congratulations!');
                            // You might want to disable further cart interactions or give other feedback
                        }
                    } else {
                        console.error("Failed to add to cart:", result.message);
                        alert("Error: " + result.message); // Simple error feedback
                    }
                } catch (error) {
                    console.error("Error adding to cart:", error);
                    alert("Error adding to cart. Please try again.");
                }
            }
        });
    }

    // Initial actions when the page loads
    fetchInitialCartCount();

    // If the product data was NOT found and rendered by Jinja, container might be empty or show "Product not found"
    // No specific JS rendering of product details is needed here anymore if Jinja handles it.
    if (container && !container.hasChildNodes() && !productIdAttribute) {
         // This case might occur if direct navigation to product-detail.html without a valid ID *and* Jinja didn't render anything.
         // Generally, Flask route should handle non-existent products before rendering the template.
        container.innerHTML = '<p class="text-center">Product details are not available. Please select a product from the main page.</p>';
    }
}); 