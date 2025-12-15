# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
"""
Lark Toolkit Example with OAuth Authentication

This example demonstrates how to use the LarkToolkit with OAuth to create,
read, and manage Lark documents and their blocks with REAL API calls.

The OAuth flow authenticates as a specific user, giving access to their
personal documents and making actions appear as performed by that user.

Prerequisites:
1. Create an app at https://open.larksuite.com/app
2. Enable OAuth 2.0 in your app settings
3. Add http://localhost:9000/callback as a redirect URI
4. Enable document permissions (docx:document, drive:drive)
5. Set environment variables:
   - LARK_APP_ID: Your application ID
   - LARK_APP_SECRET: Your application secret

Usage:
    python examples/toolkits/lark_toolkit_example.py
"""

import json
import os
import time
from pathlib import Path

from camel.toolkits import LarkToolkit
from camel.toolkits.lark_toolkit import BLOCK_TYPES

# Token storage file (in production, use a secure database)
TOKEN_FILE = Path(__file__).parent / ".lark_tokens.json"


def save_tokens(access_token: str, refresh_token: str) -> None:
    """Save tokens to file for persistence."""
    TOKEN_FILE.write_text(
        json.dumps(
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
            }
        )
    )
    print(f"Tokens saved to {TOKEN_FILE}")


def load_tokens() -> dict | None:
    """Load tokens from file if they exist."""
    if TOKEN_FILE.exists():
        return json.loads(TOKEN_FILE.read_text())
    return None


def print_result(title: str, result: dict):
    """Pretty print the result of an operation."""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    if "error" in result:
        print(f"Error: {result['error']}")
        if "code" in result:
            print(f"Code: {result['code']}")
    else:
        for key, value in result.items():
            if isinstance(value, list):
                print(f"{key}:")
                for i, item in enumerate(value[:5], 1):  # Show first 5 items
                    print(f"  {i}. {item}")
                if len(value) > 5:
                    print(f"  ... and {len(value) - 5} more items")
            else:
                print(f"{key}: {value}")


def authenticate_with_cache(toolkit: LarkToolkit) -> bool:
    """Authenticate with Lark, using cached tokens if available.

    Args:
        toolkit: The LarkToolkit instance to authenticate.

    Returns:
        bool: True if authentication was successful, False otherwise.
    """
    # Check for existing tokens
    tokens = load_tokens()
    if tokens:
        print("\nFound existing tokens. Attempting to use them...")
        toolkit.set_user_access_token(tokens["access_token"])
        toolkit.set_refresh_token(tokens["refresh_token"])

        # Try to refresh the token to ensure it's valid
        refresh_result = toolkit.refresh_user_token()
        if "error" not in refresh_result:
            print("Token refreshed successfully!")
            return True
        else:
            print("Existing tokens expired. Starting new OAuth flow...")
            TOKEN_FILE.unlink(missing_ok=True)
            toolkit.clear_user_tokens()

    # Use the new authenticate() method - handles everything automatically
    print("\nStarting OAuth authentication flow...")
    result = toolkit.authenticate()

    if "error" in result:
        print(f"Authentication failed: {result['error']}")
        return False

    return True


def main():
    """Run the Lark Toolkit example with OAuth authentication."""
    print("=" * 60)
    print("Lark Toolkit Example with OAuth Authentication")
    print("=" * 60)
    print("\nThis example uses OAuth to authenticate as a specific user.")
    print("API calls will be made with your identity and permissions.")
    print("\nMake sure you have set these environment variables:")
    app_id_set = os.environ.get("LARK_APP_ID")
    print(f"  LARK_APP_ID: {'Set' if app_id_set else 'NOT SET'}")
    print(
        f"  LARK_APP_SECRET: "
        f"{'Set' if os.environ.get('LARK_APP_SECRET') else 'NOT SET'}"
    )

    # Initialize the toolkit with token refresh callback
    toolkit = LarkToolkit(on_token_refresh=save_tokens)

    # Authenticate using the new OAuth flow
    if not authenticate_with_cache(toolkit):
        return

    # =========================================================================
    # Run Document Examples
    # =========================================================================
    print("\n" + "=" * 60)
    print("RUNNING DOCUMENT EXAMPLES")
    print("=" * 60)
    print(f"\nToolkit initialized with {len(toolkit.get_tools())} tools")
    print(
        f"Authenticated as user: "
        f"{'Yes' if toolkit.is_user_authenticated() else 'No (app-level)'}"
    )

    # =========================================================================
    # Example 1: Create a new document
    # =========================================================================
    print("\n\n1. CREATE A NEW DOCUMENT")
    print("-" * 40)
    print("Creating a new document in your Lark workspace...")

    result = toolkit.lark_create_document(
        title="CAMEL LarkToolkit Demo Document (OAuth)",
    )
    print_result("Created Document", result)

    if "error" in result:
        print("\nFailed to create document. Cannot proceed with examples.")
        print("Please check your permissions and try again.")
        return

    doc_id = result["document_id"]
    print(f"\nDocument created! ID: {doc_id}")

    # Small delay to ensure document is ready
    time.sleep(1)

    # =========================================================================
    # Example 2: Get document metadata
    # =========================================================================
    print("\n\n2. GET DOCUMENT METADATA")
    print("-" * 40)
    print(f"Fetching metadata for document: {doc_id}")

    result = toolkit.lark_get_document(document_id=doc_id)
    print_result("Document Metadata", result)

    # =========================================================================
    # Example 3: List document blocks (initially just the root page block)
    # =========================================================================
    print("\n\n3. LIST DOCUMENT BLOCKS (INITIAL STATE)")
    print("-" * 40)
    print("Listing blocks in the newly created document...")

    result = toolkit.lark_list_document_blocks(
        document_id=doc_id, page_size=50
    )
    print_result("Document Blocks", result)

    # Get the root page block ID for creating child blocks
    root_block_id = None
    if result.get("blocks"):
        root_block_id = result["blocks"][0]["block_id"]
        print(f"\nRoot page block ID: {root_block_id}")

    # =========================================================================
    # Example 4: Create a heading block
    # =========================================================================
    print("\n\n4. CREATE A HEADING BLOCK")
    print("-" * 40)
    print("Adding a heading to the document...")

    result = toolkit.lark_create_block(
        document_id=doc_id,
        block_type="heading1",
        content="Welcome to CAMEL LarkToolkit",
        parent_block_id=root_block_id,
    )
    print_result("Created Heading", result)

    # =========================================================================
    # Example 5: Create a text paragraph
    # =========================================================================
    print("\n\n5. CREATE A TEXT PARAGRAPH")
    print("-" * 40)
    print("Adding a text paragraph to the document...")

    result = toolkit.lark_create_block(
        document_id=doc_id,
        block_type="text",
        content="This document was created using the CAMEL AI LarkToolkit "
        "with OAuth. It demonstrates user-level authentication for "
        "document management.",
        parent_block_id=root_block_id,
    )
    print_result("Created Text Block", result)

    text_block_id = result.get("block_id")

    # =========================================================================
    # Example 6: Create bullet list items
    # =========================================================================
    print("\n\n6. CREATE BULLET LIST ITEMS")
    print("-" * 40)
    print("Adding bullet points to the document...")

    bullets = [
        "OAuth authentication for user-level access",
        "Create and manage documents as the authenticated user",
        "Add various block types (headings, text, lists, code)",
        "Update and delete existing blocks",
        "Automatic token refresh support",
    ]

    bullet_block_ids = []
    for bullet in bullets:
        result = toolkit.lark_create_block(
            document_id=doc_id,
            block_type="bullet",
            content=bullet,
            parent_block_id=root_block_id,
        )
        print_result(f"Created Bullet: {bullet[:30]}...", result)
        if "block_id" in result:
            bullet_block_ids.append(result["block_id"])

    # =========================================================================
    # Example 7: Create a code block
    # =========================================================================
    print("\n\n7. CREATE A CODE BLOCK")
    print("-" * 40)
    print("Adding a code block to the document...")

    code_content = """from camel.toolkits import LarkToolkit

# Initialize and authenticate with one call
toolkit = LarkToolkit()
toolkit.authenticate()

# Now use the toolkit as the authenticated user
toolkit.lark_create_document(title="My Doc")"""

    result = toolkit.lark_create_block(
        document_id=doc_id,
        block_type="code",
        content=code_content,
        parent_block_id=root_block_id,
    )
    print_result("Created Code Block", result)

    # =========================================================================
    # Example 8: Create a quote block
    # =========================================================================
    print("\n\n8. CREATE A QUOTE BLOCK")
    print("-" * 40)
    print("Adding a quote block to the document...")

    result = toolkit.lark_create_block(
        document_id=doc_id,
        block_type="quote",
        content="The best way to predict the future is to create it.",
        parent_block_id=root_block_id,
    )
    print_result("Created Quote Block", result)

    # =========================================================================
    # Example 9: Create a todo item
    # =========================================================================
    print("\n\n9. CREATE A TODO ITEM")
    print("-" * 40)
    print("Adding a todo item to the document...")

    result = toolkit.lark_create_block(
        document_id=doc_id,
        block_type="todo",
        content="Review this document",
        parent_block_id=root_block_id,
    )
    print_result("Created Todo Block", result)

    todo_block_id = result.get("block_id")

    # =========================================================================
    # Example 10: Create a divider
    # =========================================================================
    print("\n\n10. CREATE A DIVIDER")
    print("-" * 40)
    print("Adding a divider to the document...")

    result = toolkit.lark_create_block(
        document_id=doc_id,
        block_type="divider",
        content="",  # Dividers don't need content
        parent_block_id=root_block_id,
    )
    print_result("Created Divider", result)

    # =========================================================================
    # Example 11: Get document content (raw text)
    # =========================================================================
    print("\n\n11. GET DOCUMENT CONTENT")
    print("-" * 40)
    print("Fetching the document content as plain text...")

    result = toolkit.lark_get_document_content(document_id=doc_id)
    print_result("Document Content", result)

    # =========================================================================
    # Example 12: List all blocks after additions
    # =========================================================================
    print("\n\n12. LIST ALL DOCUMENT BLOCKS (AFTER ADDITIONS)")
    print("-" * 40)
    print("Listing all blocks in the document now...")

    result = toolkit.lark_list_document_blocks(
        document_id=doc_id, page_size=50
    )
    print_result("Document Blocks", result)

    # =========================================================================
    # Example 13: Get a specific block
    # =========================================================================
    if text_block_id:
        print("\n\n13. GET A SPECIFIC BLOCK")
        print("-" * 40)
        print(f"Fetching details for block: {text_block_id}")

        result = toolkit.lark_get_block(
            document_id=doc_id, block_id=text_block_id
        )
        print_result("Block Details", result)

    # =========================================================================
    # Example 14: Update an existing block
    # =========================================================================
    if text_block_id:
        print("\n\n14. UPDATE AN EXISTING BLOCK")
        print("-" * 40)
        print(f"Updating the text block: {text_block_id}")

        result = toolkit.lark_update_block(
            document_id=doc_id,
            block_id=text_block_id,
            content="[UPDATED] This document was created and modified using "
            "the CAMEL AI LarkToolkit with OAuth authentication. The toolkit "
            "provides powerful document management with user-level access.",
        )
        print_result("Updated Block", result)

    # =========================================================================
    # Example 15: Batch update blocks
    # =========================================================================
    print("\n\n15. BATCH UPDATE BLOCKS")
    print("-" * 40)
    print("Performing batch operations...")

    operations = [
        {
            "action": "create",
            "block_type": "heading2",
            "content": "Additional Notes",
        },
        {
            "action": "create",
            "block_type": "text",
            "content": "This section was added via batch operations.",
        },
    ]

    # Add an update operation if we have a todo block
    if todo_block_id:
        operations.append(
            {
                "action": "update",
                "block_id": todo_block_id,
                "content": "[COMPLETED] Review this document",
            }
        )

    result = toolkit.lark_batch_update_blocks(
        document_id=doc_id, operations=operations
    )
    print_result("Batch Update Results", result)

    # =========================================================================
    # Summary
    # =========================================================================
    print("\n\n" + "=" * 60)
    print("EXAMPLE COMPLETED SUCCESSFULLY!")
    print("=" * 60)

    print(f"\nDocument URL: https://larksuite.com/docx/{doc_id}")
    print("\nOpen this URL in your browser to view the created document.")

    print(f"\nTotal tools available: {len(toolkit.get_tools())}")
    print("\nAvailable tools:")
    for i, tool in enumerate(toolkit.get_tools(), 1):
        print(f"  {i}. {tool.func.__name__}")

    print("\nSupported block types:")
    for block_type, type_id in BLOCK_TYPES.items():
        print(f"  - {block_type} (type_id: {type_id})")

    print("\n" + "=" * 60)
    print("Remember to check your Lark workspace for the new document!")
    print("=" * 60)


if __name__ == "__main__":
    main()
