document.addEventListener('DOMContentLoaded', () => {
    const productContainer = document.getElementById('smain');
    const searchInput = document.querySelector('#_inp input[type="search"]');
    const categorySelect = document.querySelector('#_inp select');
    const cartCountElement = document.getElementById('c0');

    let allProducts = []; // To store products fetched from API

    // Function to fetch products from API
    async function fetchProducts() {
        try {
            const response = await fetch('/api/products');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            allProducts = await response.json();
            displayProducts(allProducts); // Display all products initially
        } catch (error) {
            console.error("Could not fetch products:", error);
            if (productContainer) {
                productContainer.innerHTML = "<p class='text-center text-danger'>Could not load products. Please try again later.</p>";
            }
        }
    }

    // Function to display products
    function displayProducts(productArray) {
        if (!productContainer) {
            console.error("Product container 'smain' not found.");
            return;
        }
        productContainer.innerHTML = ''; // Clear existing products
        
        const productGrid = document.createElement('div');
        productGrid.className = "container-fluid d-flex justify-content-center flex-wrap flex-md-nowrap container-xxl p-0";

        if (productArray.length === 0) {
            productGrid.innerHTML = "<p class='text-center w-100'>No products found matching your criteria.</p>";
        }

        productArray.forEach(product => {
            const productDiv = document.createElement('div');
            productDiv.className = 'pic p-0 m-0 col-4 col-lg-3';
            
            let stars = '';
            for (let i = 0; i < 5; i++) {
                if (i < Math.floor(product.rating)) {
                    stars += '<i class="bi bi-star-fill text-warning"></i>';
                } else if (i < product.rating && product.rating % 1 !== 0) {
                    stars += '<i class="bi bi-star-half text-warning"></i>';
                } else {
                    stars += '<i class="bi bi-star text-warning"></i>';
                }
            }

            // Note: Product image path now needs to be prefixed with static path if not already handled by Flask's url_for in template
            // However, since product.image comes from the API, it should already be correct if defined correctly in app.py products list.
            productDiv.innerHTML = `
                <a href="/product/${product.id}" class="text-decoration-none text-dark">
                    <h5 class="col-12 d-flex align-items-center p-0 m-0">${product.name}</h5>
                    <div class="col-12 row p-0 m-0">
                        <img class="col-12" src="/static/${product.image}" alt="${product.name}" style="height: 150px; object-fit: cover;">
                    </div>
                </a>
                <div class="col-12 p-2">
                    <div>${stars} (${product.rating})</div>
                    <div>Price: $${product.price}</div>
                    <!-- <div class="mt-auto">
                        <button class="btn btn-warning w-100 add-to-cart" data-id="${product.id}">Add to Cart</button>
                    </div> -->
                </div>
            `;
            productGrid.appendChild(productDiv);
        });
        productContainer.appendChild(productGrid);

        // For buttons initially rendered by Jinja:
        // productContainer.addEventListener('click', function(event) {
        //    if (event.target.matches('.add-to-cart')) {
        //        handleAddToCart(event);
        //    }
        // });
        // No longer needed if homepage cards don't have add-to-cart buttons.
        // Search result add-to-cart buttons (if any were kept) would be handled by direct re-attachment in displayProducts.
    }

    // Function to handle search
    function handleSearch() {
        const searchTerm = searchInput.value.toLowerCase();
        const category = categorySelect.value;

        const filteredProducts = allProducts.filter(product => {
            const nameMatches = product.name.toLowerCase().includes(searchTerm);
            const categoryMatches = category === "All" || product.category === category;
            return nameMatches && categoryMatches;
        });
        displayProducts(filteredProducts);
    }

    // Function to add item to cart via API
    async function handleAddToCart(event) {
        const productId = parseInt(event.target.dataset.id);
        try {
            const response = await fetch('/api/cart/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ productId: productId, quantity: 1 })
            });
            const result = await response.json();
            if (result.success) {
                updateCartDisplay(result.cart_count);
                // Optionally show a success message
                console.log(result.message);
                if (result.task_completed) {
                    alert('Task Complete! Congratulations!');
                    // You might want to disable further cart interactions or give other feedback
                }
            } else {
                console.error("Failed to add to cart:", result.message);
                // Optionally show an error message to the user
            }
        } catch (error) {
            console.error("Error adding to cart:", error);
        }
    }

    // Function to update cart display count
    function updateCartDisplay(count) {
        if (cartCountElement) {
            cartCountElement.textContent = count;
        }
    }

    // Fetch initial cart count
    async function fetchInitialCartCount() {
        try {
            const response = await fetch('/api/cart');
            const currentCart = await response.json();
            updateCartDisplay(currentCart.length);
        } catch (error) {
            console.error("Error fetching initial cart state:", error);
            updateCartDisplay(0);
        }
    }

    // Event listeners for search and category select
    if (searchInput) {
        searchInput.addEventListener('input', handleSearch);
    }
    if (categorySelect) {
        categorySelect.addEventListener('change', handleSearch);
    }

    // Initial setup
    fetchProducts();
    fetchInitialCartCount();

    // --- Existing Menu Toggle Functionality --- //
    // (Keep the menu toggle JS as it is, it's not related to products/cart)
    document.getElementById('all').addEventListener('click', function(){
        document.getElementById('lmenu').classList.remove('lm')
        document.getElementById('x').style.display = "flex"
        document.getElementById('fullsc').style.display = 'flex'
    });
    document.getElementById('x').addEventListener('click', function(){
      document.getElementById('lmenu').classList.add('lm')
        document.getElementById('x').style.display = "none"
        document.getElementById('fullsc').style.display = 'none'
    });
    document.getElementById('activDnMenu').addEventListener('click' , function(){
      document.getElementById('dnMenu').classList.toggle('d2')
      document.getElementById('_icon1').classList.toggle('bi-chevron-down')
      document.getElementById('_icon1').classList.toggle('bi-chevron-up')
    });
    document.getElementById('activDnMenu2').addEventListener('click' , function(){
      document.getElementById('dnMenu2').classList.toggle('d2')
      document.getElementById('_icon2').classList.toggle('bi-chevron-down')
      document.getElementById('_icon2').classList.toggle('bi-chevron-up')
    });
});

// Make functions globally available if needed by other scripts (legacy from previous structure)
// window.addToCart = handleAddToCart; // This was for the old addToCart. Now direct API calls are preferred.
// window.updateCartDisplay = updateCartDisplay; // This can be kept if product-detail/cart-page call it directly.
// It is better if each page manages its own cart updates based on API calls or data from Flask.

// Cleaned up global namespace: script.js should not expose addToCart or cart array anymore.
// If other scripts need to update the cart display, they should have their own logic or call a shared updateCartDisplay function.
// For simplicity in this refactor, we will assume product-detail.js and cart-page.js will manage their own cart count updates
// or that the count is primarily updated by Flask template rendering.