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
Lark OAuth Example - Full User Authentication Flow

This example demonstrates how to use OAuth to authenticate as a specific user
and make API calls with their permissions.

Prerequisites:
1. Create a Lark app at https://open.larksuite.com/app
2. Enable OAuth 2.0 in your app settings
3. Add http://localhost:3000/callback as a redirect URI
4. Grant the following permissions to your app:
   - docx:document (Read and write documents)
   - drive:drive (Access Drive)
5. Set environment variables:
   - LARK_APP_ID: Your app ID
   - LARK_APP_SECRET: Your app secret

Usage:
    pip install flask
    python lark_oauth_example.py

Then open http://localhost:3000 in your browser to start the OAuth flow.
"""

import json
import os
import secrets
import webbrowser
from pathlib import Path
from threading import Timer

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


def main():
    """Run the OAuth example with a Flask web server."""
    try:
        from flask import Flask, redirect, request
    except ImportError:
        print("Flask is required for this example.")
        print("Install it with: pip install flask")
        return

    from camel.toolkits import LarkToolkit

    app = Flask(__name__)

    # Generate a random state for CSRF protection
    oauth_state = secrets.token_urlsafe(16)

    # Initialize the toolkit with OAuth redirect URI
    toolkit = LarkToolkit(
        oauth_redirect_uri="http://localhost:3000/callback",
        on_token_refresh=save_tokens,
    )

    @app.route("/")
    def index():
        """Home page with login link."""
        # Check if we have existing tokens
        tokens = load_tokens()
        if tokens:
            toolkit.set_user_access_token(tokens["access_token"])
            toolkit.set_refresh_token(tokens["refresh_token"])
            return redirect("/dashboard")

        # Generate OAuth URL
        auth_url = toolkit.get_oauth_url(state=oauth_state)

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Lark OAuth Example</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont,
                        'Segoe UI', Roboto, sans-serif;
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .card {{
                    background: white;
                    border-radius: 8px;
                    padding: 30px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                h1 {{ color: #333; }}
                .btn {{
                    display: inline-block;
                    background: #3370ff;
                    color: white;
                    padding: 12px 24px;
                    border-radius: 6px;
                    text-decoration: none;
                    font-weight: 500;
                    margin-top: 20px;
                }}
                .btn:hover {{ background: #2860e0; }}
                code {{
                    background: #f0f0f0;
                    padding: 2px 6px;
                    border-radius: 4px;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="card">
                <h1>Lark OAuth Example</h1>
                <p>This example demonstrates OAuth with Lark.</p>
                <p>Click the button below to sign in with Lark:</p>
                <a href="{auth_url}" class="btn">Sign in with Lark</a>
                <hr style="margin: 30px 0;">
                <h3>What happens next?</h3>
                <ol>
                    <li>You'll be redirected to Lark's login page</li>
                    <li>After login, you'll grant permissions to this app</li>
                    <li>Lark redirects back with an authorization code</li>
                    <li>We exchange the code for access tokens</li>
                    <li>You can then make API calls as yourself!</li>
                </ol>
            </div>
        </body>
        </html>
        """

    @app.route("/callback")
    def callback():
        """Handle OAuth callback from Lark."""
        # Verify state to prevent CSRF
        state = request.args.get("state", "")
        if state != oauth_state:
            return "Invalid state parameter. Possible CSRF attack.", 400

        # Get authorization code
        code = request.args.get("code")
        if not code:
            error = request.args.get("error", "Unknown error")
            return f"Authorization failed: {error}", 400

        # Exchange code for tokens
        print(f"Received authorization code: {code[:20]}...")
        result = toolkit.exchange_code_for_token(code)

        if "error" in result:
            return (
                f"""
            <h1>Authentication Failed</h1>
            <p>Error: {result['error']}</p>
            <p><a href="/">Try again</a></p>
            """,
                400,
            )

        # Save tokens
        save_tokens(result["user_access_token"], result["refresh_token"])

        return redirect("/dashboard")

    @app.route("/dashboard")
    def dashboard():
        """Dashboard showing user info and document operations."""
        # Load tokens if not already set
        if not toolkit.is_user_authenticated():
            tokens = load_tokens()
            if not tokens:
                return redirect("/")
            toolkit.set_user_access_token(tokens["access_token"])
            toolkit.set_refresh_token(tokens["refresh_token"])

        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Lark OAuth - Dashboard</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont,
                        'Segoe UI', Roboto, sans-serif;
                    max-width: 900px;
                    margin: 50px auto;
                    padding: 20px;
                    background: #f5f5f5;
                }
                .card {
                    background: white;
                    border-radius: 8px;
                    padding: 30px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    margin-bottom: 20px;
                }
                h1 { color: #333; }
                .btn {
                    display: inline-block;
                    background: #3370ff;
                    color: white;
                    padding: 10px 20px;
                    border-radius: 6px;
                    text-decoration: none;
                    font-weight: 500;
                    margin: 5px;
                }
                .btn:hover { background: #2860e0; }
                .btn-danger { background: #ff4d4f; }
                .btn-danger:hover { background: #ff7875; }
                .btn-success { background: #52c41a; }
                .btn-success:hover { background: #73d13d; }
                pre {
                    background: #1e1e1e;
                    color: #d4d4d4;
                    padding: 15px;
                    border-radius: 6px;
                    overflow-x: auto;
                    font-size: 13px;
                }
                .success { color: #52c41a; }
                .error { color: #ff4d4f; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>Dashboard</h1>
                <p class="success">You are authenticated with Lark!</p>
                <p>Try the following operations:</p>
                <a href="/create-doc" class="btn btn-success">Create Doc</a>
                <a href="/refresh-token" class="btn">Refresh Token</a>
                <a href="/logout" class="btn btn-danger">Logout</a>
            </div>
            <div class="card">
                <h3>API Test Results</h3>
                <p>Click a button above to test the OAuth integration.</p>
            </div>
        </body>
        </html>
        """

    @app.route("/create-doc")
    def create_doc():
        """Create a test document using the user's permissions."""
        if not toolkit.is_user_authenticated():
            tokens = load_tokens()
            if not tokens:
                return redirect("/")
            toolkit.set_user_access_token(tokens["access_token"])
            toolkit.set_refresh_token(tokens["refresh_token"])

        # Create a document
        print("Creating document with user permissions...")
        result = toolkit.lark_create_document(
            title="Test Document (Created via OAuth)"
        )

        if "error" in result:
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Create Document - Error</title>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont,
                        'Segoe UI', Roboto, sans-serif;
                        max-width: 800px;
                        margin: 50px auto;
                        padding: 20px;
                    }}
                    .card {{
                        background: white;
                        border-radius: 8px;
                        padding: 30px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }}
                    .error {{ color: #ff4d4f; }}
                    pre {{
                        background: #1e1e1e;
                        color: #d4d4d4;
                        padding: 15px;
                        border-radius: 6px;
                    }}
                    a {{ color: #3370ff; }}
                </style>
            </head>
            <body>
                <div class="card">
                    <h1 class="error">Failed to Create Document</h1>
                    <pre>{json.dumps(result, indent=2)}</pre>
                    <p>This might be due to:</p>
                    <ul>
                        <li>Missing permissions (docx:document)</li>
                        <li>Expired token - try
                            <a href="/refresh-token">refreshing</a></li>
                    </ul>
                    <p><a href="/dashboard">Back to Dashboard</a></p>
                </div>
            </body>
            </html>
            """

        # Add some content to the document
        doc_id = result["document_id"]
        toolkit.lark_create_block(
            document_id=doc_id,
            block_type="heading1",
            content="Hello from CAMEL!",
        )
        toolkit.lark_create_block(
            document_id=doc_id,
            block_type="text",
            content="This document was created using OAuth authentication.",
        )
        toolkit.lark_create_block(
            document_id=doc_id,
            block_type="bullet",
            content="The LarkToolkit now supports user access tokens",
        )
        toolkit.lark_create_block(
            document_id=doc_id,
            block_type="bullet",
            content="All API calls are made with your identity",
        )
        toolkit.lark_create_block(
            document_id=doc_id,
            block_type="bullet",
            content="You have full access to your personal documents",
        )

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Document Created!</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont,
                        'Segoe UI', Roboto, sans-serif;
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                }}
                .card {{
                    background: white;
                    border-radius: 8px;
                    padding: 30px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .success {{ color: #52c41a; }}
                pre {{
                    background: #1e1e1e;
                    color: #d4d4d4;
                    padding: 15px;
                    border-radius: 6px;
                }}
                .btn {{
                    display: inline-block;
                    background: #3370ff;
                    color: white;
                    padding: 10px 20px;
                    border-radius: 6px;
                    text-decoration: none;
                }}
            </style>
        </head>
        <body>
            <div class="card">
                <h1 class="success">Document Created Successfully!</h1>
                <p>A new document has been created in your Lark Drive:</p>
                <pre>{json.dumps(result, indent=2)}</pre>
                <p>
                    <a href="{result.get('url', '#')}"
                        target="_blank" class="btn">
                        Open Document in Lark
                    </a>
                </p>
                <p style="margin-top: 20px;">
                    <a href="/dashboard">Back to Dashboard</a>
                </p>
            </div>
        </body>
        </html>
        """

    @app.route("/refresh-token")
    def refresh_token():
        """Refresh the access token."""
        tokens = load_tokens()
        if not tokens:
            return redirect("/")

        toolkit.set_refresh_token(tokens["refresh_token"])
        result = toolkit.refresh_user_token()

        if "error" in result:
            # Token refresh failed, need to re-authenticate
            TOKEN_FILE.unlink(missing_ok=True)
            return f"""
            <h1>Token Refresh Failed</h1>
            <p>Error: {result['error']}</p>
            <p>Session expired. Please <a href="/">login again</a>.</p>
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Token Refreshed</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont,
                        'Segoe UI', Roboto, sans-serif;
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                }}
                .card {{
                    background: white;
                    border-radius: 8px;
                    padding: 30px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .success {{ color: #52c41a; }}
                pre {{
                    background: #1e1e1e;
                    color: #d4d4d4;
                    padding: 15px;
                    border-radius: 6px;
                }}
            </style>
        </head>
        <body>
            <div class="card">
                <h1 class="success">Token Refreshed Successfully!</h1>
                <p>Your access token has been refreshed:</p>
                <pre>{{
    "expires_in": {result.get('expires_in', 'N/A')} seconds,
    "access_token": "{result.get('user_access_token', '')[:30]}...",
    "refresh_token": "{result.get('refresh_token', '')[:30]}..."
}}</pre>
                <p><a href="/dashboard">Back to Dashboard</a></p>
            </div>
        </body>
        </html>
        """

    @app.route("/logout")
    def logout():
        """Clear tokens and logout."""
        TOKEN_FILE.unlink(missing_ok=True)
        toolkit.clear_user_tokens()
        return redirect("/")

    # Open browser automatically after a short delay
    def open_browser():
        webbrowser.open("http://localhost:3000")

    print("\n" + "=" * 60)
    print("Lark OAuth Example")
    print("=" * 60)
    print("\nMake sure you have set these environment variables:")
    app_id_status = "Set" if os.environ.get("LARK_APP_ID") else "NOT SET"
    secret_set = os.environ.get("LARK_APP_SECRET")
    app_secret_status = "Set" if secret_set else "NOT SET"
    print(f"  LARK_APP_ID: {app_id_status}")
    print(f"  LARK_APP_SECRET: {app_secret_status}")
    print("\nStarting server at http://localhost:3000")
    print("Opening browser in 2 seconds...")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 60 + "\n")

    Timer(2.0, open_browser).start()
    app.run(host="localhost", port=3000, debug=False)


if __name__ == "__main__":
    main()
