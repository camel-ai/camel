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
Lark OAuth Example - Simplified User Authentication Flow

This example demonstrates how to use the simplified OAuth flow to authenticate
as a specific user and make API calls with their permissions.

Prerequisites:
1. Create a Lark app at https://open.larksuite.com/app
2. Enable OAuth 2.0 in your app settings
3. Add http://localhost:9000/callback as a redirect URI
4. Grant the following permissions to your app:
   - docx:document (Read and write documents)
   - drive:drive (Access Drive)
5. Set environment variables:
   - LARK_APP_ID: Your app ID
   - LARK_APP_SECRET: Your app secret

Usage:
    python lark_oauth_example.py
"""

import os

from camel.toolkits import LarkToolkit


def main():
    """Run the simplified OAuth example."""
    print("\n" + "=" * 60)
    print("Lark OAuth Example (Simplified Flow)")
    print("=" * 60)

    # Check environment variables
    app_id_status = "Set" if os.environ.get("LARK_APP_ID") else "NOT SET"
    app_secret_status = (
        "Set" if os.environ.get("LARK_APP_SECRET") else "NOT SET"
    )
    print(f"\nLARK_APP_ID: {app_id_status}")
    print(f"LARK_APP_SECRET: {app_secret_status}")

    if not os.environ.get("LARK_APP_ID") or not os.environ.get(
        "LARK_APP_SECRET"
    ):
        print("\nPlease set the required environment variables first.")
        return

    # Initialize toolkit
    toolkit = LarkToolkit()

    # Authenticate using the simplified browser flow
    print("\n" + "-" * 60)
    print("Starting OAuth authentication...")
    print("-" * 60)

    result = toolkit.authenticate(
        port=9000,
        timeout=120,
        open_browser=True,
    )

    if "error" in result:
        print(f"\nAuthentication failed: {result['error']}")
        return

    print("\n" + "-" * 60)
    print("Authentication successful!")
    print("-" * 60)
    print(
        f"Access token expires in: {result.get('expires_in', 'N/A')} seconds"
    )

    # Test the authentication by creating a document
    print("\n" + "-" * 60)
    print("Testing API access: Creating a document...")
    print("-" * 60)

    doc_result = toolkit.lark_create_document(
        title="Test Document (Created via OAuth)"
    )

    if "error" in doc_result:
        print(f"\nFailed to create document: {doc_result['error']}")
        print("\nThis might be due to missing permissions (docx:document)")
        return

    print("\nDocument created successfully!")
    print(f"  Document ID: {doc_result.get('document_id')}")
    print(f"  URL: {doc_result.get('url')}")

    print("\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
