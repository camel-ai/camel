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

This example demonstrates how to use the LarkToolkit with OAuth to delete
a block from a Lark document.

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

import os
import time

from camel.toolkits import LarkToolkit


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


def main():
    """Run the Lark Toolkit example with OAuth authentication."""
    print("=" * 60)
    print("Lark Toolkit Example - Delete a Block")
    print("=" * 60)

    # Check environment variables
    if not os.environ.get("LARK_APP_ID") or not os.environ.get(
        "LARK_APP_SECRET"
    ):
        print("\nPlease set the required environment variables first.")
        app_id = os.environ.get("LARK_APP_ID")
        app_secret = os.environ.get("LARK_APP_SECRET")
        print(f"  LARK_APP_ID: {'Set' if app_id else 'NOT SET'}")
        print(f"  LARK_APP_SECRET: {'Set' if app_secret else 'NOT SET'}")
        return

    # Initialize toolkit
    toolkit = LarkToolkit()

    # Authenticate
    print("\nStarting OAuth authentication...")
    result = toolkit.authenticate(
        port=9000,
        timeout=120,
        open_browser=True,
    )

    if "error" in result:
        print(f"\nAuthentication failed: {result['error']}")
        return

    print("\nAuthentication successful!")

    # Get root folder token
    result = toolkit.lark_get_root_folder_token()
    root_folder_token = result.get("token") if "error" not in result else None

    # Create a document to work with
    print("\nCreating a test document...")
    result = toolkit.lark_create_document(
        title="CAMEL Delete Block Demo",
        folder_token=root_folder_token,
    )

    if "error" in result:
        print(f"\nFailed to create document: {result['error']}")
        return

    doc_id = result["document_id"]
    print(f"Document created! ID: {doc_id}")

    time.sleep(1)

    # Get root block ID
    result = toolkit.lark_list_document_blocks(
        document_id=doc_id, page_size=50
    )
    root_block_id = None
    if result.get("blocks"):
        root_block_id = result["blocks"][0]["block_id"]

    # Create a block to delete
    print("\nCreating a block to delete...")
    result = toolkit.lark_create_block(
        document_id=doc_id,
        block_type="text",
        content="This block will be deleted.",
        parent_block_id=root_block_id,
    )
    print_result("Created Block", result)

    block_to_delete = result.get("block_id")

    if block_to_delete:
        # =====================================================================
        # Delete a block
        # =====================================================================
        print("\n\nDELETE A BLOCK")
        print("-" * 40)
        print(f"Deleting block: {block_to_delete}")

        result = toolkit.lark_delete_block(
            document_id=doc_id, block_id=block_to_delete
        )
        print_result("Deleted Block", result)

    print("\n" + "=" * 60)
    print("EXAMPLE COMPLETED!")
    print("=" * 60)
    print(f"\nDocument URL: https://larksuite.com/docx/{doc_id}")


if __name__ == "__main__":
    main()
