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
import json
import os
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from camel.toolkits.zoho_toolkit import ZohoMailToolkit


def main():
    datacenter = os.getenv("ZOHO_DATACENTER", "com")
    client_id = (
        os.getenv("ZOHO_CLIENT_ID") or input("Enter ZOHO_CLIENT_ID: ").strip()
    )
    client_secret = (
        os.getenv("ZOHO_CLIENT_SECRET")
        or input("Enter ZOHO_CLIENT_SECRET: ").strip()
    )
    redirect_uri = os.getenv("ZOHO_REDIRECT_URI", "").strip()
    scopes = os.getenv(
        "ZOHO_SCOPES",
        "ZohoMail.messages.ALL,ZohoMail.accounts.ALL,ZohoMail.folders.ALL,ZohoMail.tags.ALL",
    )

    # If no redirect URI provided, start a local redirect server and use it
    holder = {"code": None, "location": None, "accounts_server": None}
    server_thread = None
    if not redirect_uri:
        redirect_host = "127.0.0.1"
        redirect_port = 8000
        redirect_path = "/callback"
        redirect_uri = f"http://{redirect_host}:{redirect_port}{redirect_path}"

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urlparse(self.path)
                if parsed.path == redirect_path:
                    params = parse_qs(parsed.query)
                    holder["code"] = params.get("code", [None])[0]
                    holder["location"] = params.get("location", [None])[0]
                    holder["accounts_server"] = params.get(
                        "accounts-server", [None]
                    )[0]
                    self.send_response(200)
                    self.send_header(
                        "Content-Type", "text/html; charset=utf-8"
                    )
                    self.end_headers()
                    self.wfile.write(
                        b"<html><body>Authorization received. You can close this tab.</body></html>"  # noqa: E501
                    )
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, fmt, *args):
                return

        def run_server():
            httpd = HTTPServer((redirect_host, redirect_port), Handler)
            try:
                httpd.handle_request()
            except Exception:
                pass

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

    auth_url = ZohoMailToolkit.build_authorize_url(
        client_type="server",
        client_id=client_id,
        scope=scopes,
        redirect_uri=redirect_uri,
        access_type="offline",
        dc=datacenter,
        prompt="consent",
    )
    print(
        "\nOpen this URL in your browser and authorize, then paste the 'code':"
    )
    print(auth_url)
    try:
        webbrowser.open(auth_url)
    except Exception:
        pass
    code = None
    if server_thread is not None:
        # wait up to 180 seconds for redirect
        for _ in range(180):
            if holder["code"]:
                code = holder["code"]
                break
            time.sleep(1)

    temp = ZohoMailToolkit(access_token="", account_id="", datacenter="in")
    token_resp = temp.exchange_code_for_token(
        code=code,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=scopes,
    )
    print("\nToken response:")
    print(json.dumps(token_resp, indent=2))
    access_token = token_resp.get("access_token") or ""
    if not access_token:
        print("Failed to obtain access token.")
        return

    identifier = os.getenv("ZOHO_ACCOUNT_ID", "").strip()
    if not identifier:
        identifier = input(
            "Enter ZOHO_ACCOUNT_ID (numeric or email, leave blank to auto): "
        ).strip()
    if identifier.isdigit():
        account_id, default_from_email = identifier, ""
    else:
        account_id, default_from_email = (
            ZohoMailToolkit.resolve_account_id_static(
                datacenter, access_token, identifier
            )
        )
    if not account_id or not account_id.isdigit():
        print("Failed to resolve numeric ZOHO_ACCOUNT_ID.")
        return
    toolkit = ZohoMailToolkit(
        access_token=access_token, account_id=account_id, datacenter=datacenter
    )

    # Action: Send Email
    to_email = (
        os.getenv("ZOHO_TO_ADDRESS")
        or input("Enter recipient email: ").strip()
    )
    from_email = os.getenv("ZOHO_FROM_ADDRESS", "") or (
        default_from_email or None
    )
    send_resp = toolkit.send_email(
        to=[to_email],
        subject="Zoho Mail - Send Email (CAMEL)",
        content="This is a test email sent via ZohoMailToolkit (focused).",
        is_html=False,
        from_email=from_email,
    )
    print("\nSend Email response:")
    print(json.dumps(send_resp, indent=2))

    # Action: Create Draft
    draft_resp = toolkit.create_draft(
        to=[to_email],
        subject="Draft from CAMEL",
        content="This is a draft created via ZohoMailToolkit.",
        is_html=False,
        from_email=from_email,
    )
    print("\nCreate Draft response:")
    print(json.dumps(draft_resp, indent=2))

    # Action: Create Folder
    folder_resp = toolkit.create_folder(name="CAMEL_Demo")
    print("\nCreate Folder response:")
    print(json.dumps(folder_resp, indent=2))
    created_folder_id = None
    if isinstance(folder_resp, dict):
        created_folder_id = folder_resp.get("folderId") or folder_resp.get(
            "id"
        )

    # Action: Create Tag
    tag_resp = toolkit.create_tag(name="CAMEL_Tag")
    print("\nCreate Tag response:")
    print(json.dumps(tag_resp, indent=2))
    created_tag_id = None
    if isinstance(tag_resp, dict):
        created_tag_id = tag_resp.get("labelId") or tag_resp.get("id")

    # Action: Create Task
    task_resp = toolkit.create_task(
        title="Follow up", description="Call customer", due_in_epoch_ms=None
    )
    print("\nCreate Task response:")
    print(json.dumps(task_resp, indent=2))

    # Triggers (Polling)
    print("\nTrigger: New Email (Polling)")
    poll_resp = toolkit.trigger_new_email_poll(
        folder_id=str(created_folder_id) if created_folder_id else "inbox",
        limit=10,
    )
    print(json.dumps(poll_resp, indent=2))

    print("\nTrigger: New Email Matching Search (Polling)")
    search_resp = toolkit.trigger_new_email_matching_search_poll(
        query=f'from:"{to_email}"', folder_id="inbox", limit=10
    )
    print(json.dumps(search_resp, indent=2))

    if created_tag_id:
        print("\nTrigger: New Tagged Email (Polling)")
        tagged_resp = toolkit.trigger_new_tagged_email_poll(
            tag_id=str(created_tag_id), folder_id="inbox", limit=10
        )
        print(json.dumps(tagged_resp, indent=2))


if __name__ == "__main__":
    main()
