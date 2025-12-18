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
Lark Folder Test - Direct API Testing

This script tests lark_create_document() and lark_list_folder_contents().

Prerequisites:
1. Create an app at https://open.larksuite.com/app
2. Enable OAuth 2.0 and add http://localhost:9000/callback as redirect URI
3. Enable permissions: drive:drive, drive:drive:readonly, docx:document
4. Set environment variables:
   - LARK_APP_ID: Your application ID
   - LARK_APP_SECRET: Your application secret

Usage:
    python examples/toolkits/lark_folder_test.py
"""

import json
import os

from camel.toolkits import LarkToolkit


def print_header(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


def print_result(result: dict):
    """Pretty print a result dictionary."""
    print(json.dumps(result, indent=2, default=str))


def main():
    print_header("Lark Folder Test")

    # Check environment variables
    print("\n[1] Checking environment variables...")
    app_id = os.environ.get("LARK_APP_ID")
    app_secret = os.environ.get("LARK_APP_SECRET")
    print(f"    LARK_APP_ID: {'Set' if app_id else 'NOT SET'}")
    print(f"    LARK_APP_SECRET: {'Set' if app_secret else 'NOT SET'}")

    if not app_id or not app_secret:
        print("\nERROR: Please set the required environment variables first.")
        return

    # Initialize toolkit
    print("\n[2] Initializing LarkToolkit...")
    toolkit = LarkToolkit()
    print("    Toolkit initialized successfully")

    # Authenticate
    print("\n[3] Starting OAuth authentication...")
    print("    A browser window will open for you to log in to Lark.")
    auth_result = toolkit.authenticate(
        port=9000,
        timeout=120,
        open_browser=True,
    )

    if "error" in auth_result:
        print(f"\nERROR: Authentication failed: {auth_result['error']}")
        return

    print("    Authentication successful!")
    print(f"    Token expires in: {auth_result.get('expires_in')} seconds")
    print(f"    Scopes granted: {auth_result.get('scope')}")

    # Test 1: Create a document called "document test"
    # Using lark_create_document_http to ensure document is owned by the user
    print_header("TEST 1: Create Document (HTTP)")
    doc_title = "document test"
    print(f"Calling: toolkit.lark_create_document_http(title='{doc_title}')")
    create_result = toolkit.lark_create_document_http(title=doc_title)
    print("\nResult:")
    print_result(create_result)

    if "error" in create_result:
        print("\nFAILED: Could not create document")
        return

    created_doc_id = create_result.get("document_id")
    print(f"\nCreated document ID: {created_doc_id}")

    # Test 2: List all documents from root
    print_header("TEST 2: List Root Folder Contents")
    print("Calling: toolkit.lark_list_folder_contents()")
    list_result = toolkit.lark_list_folder_contents()
    print("\nResult:")
    print_result(list_result)

    if "error" in list_result:
        print("\nFAILED: Could not list folder contents")
        return

    # Extract URL of "document test"
    print_header("Extract 'document test' URL")
    files = list_result.get("files", [])
    document_test_url = None

    for file in files:
        if file.get("name") == "document test":
            document_test_url = file.get("url")
            print("Found 'document test':")
            print(f"  - Token: {file.get('token')}")
            print(f"  - Type: {file.get('type')}")
            print(f"  - URL: {document_test_url}")
            break

    if not document_test_url:
        print("Could not find 'document test' in the file list.")
        print("It may be that the document was created but not yet indexed.")
        print(f"Try the URL from creation: {create_result.get('url')}")
        document_test_url = create_result.get("url")

    # Summary
    print_header("SUMMARY")
    print("Tests completed!")
    print(f"  - Created document: {doc_title}")
    print(f"  - Document ID: {created_doc_id}")
    print(f"  - Document URL: {document_test_url}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
