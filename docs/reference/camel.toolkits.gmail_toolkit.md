<a id="camel.toolkits.gmail_toolkit"></a>

<a id="camel.toolkits.gmail_toolkit.GmailToolkit"></a>

## GmailToolkit

```python
class GmailToolkit(BaseToolkit):
```

A comprehensive toolkit for Gmail operations.

This toolkit provides methods for Gmail operations including sending emails,
managing drafts, fetching messages, managing labels, and handling contacts.
It supports both plain text and HTML email formats, attachment handling,
and comprehensive Gmail API integration.

**Parameters:**

- **timeout** (Optional[float]): The timeout value for API requests in seconds. If None, no timeout is applied. (default: :obj:`None`)

**Note:**

This toolkit requires Google OAuth2 authentication. On first use, it will open a browser window for authentication and store credentials for future use.

**Authentication Scopes:**

The toolkit requests the following Gmail API scopes:
- `https://www.googleapis.com/auth/gmail.readonly` - Read-only access
- `https://www.googleapis.com/auth/gmail.send` - Send emails
- `https://www.googleapis.com/auth/gmail.modify` - Modify emails
- `https://www.googleapis.com/auth/gmail.compose` - Compose emails
- `https://www.googleapis.com/auth/gmail.labels` - Manage labels
- `https://www.googleapis.com/auth/contacts.readonly` - Read contacts
- `https://www.googleapis.com/auth/userinfo.profile` - User profile access

<a id="camel.toolkits.gmail_toolkit.GmailToolkit.__init__"></a>

### __init__

```python
def __init__(
    self,
    timeout: Optional[float] = None,
):
```

Initialize a new instance of the GmailToolkit class.

**Parameters:**

- **timeout** (Optional[float]): The timeout value for API requests in seconds. If None, no timeout is applied. (default: :obj:`None`)

<a id="camel.toolkits.gmail_toolkit.GmailToolkit.send_email"></a>

### send_email

```python
def send_email(
    self,
    to: Union[str, List[str]],
    subject: str,
    body: str,
    cc: Optional[Union[str, List[str]]] = None,
    bcc: Optional[Union[str, List[str]]] = None,
    attachments: Optional[List[str]] = None,
    is_html: bool = False,
) -> Dict[str, Any]:
```

Send an email through Gmail.

**Parameters:**

- **to** (Union[str, List[str]]): Recipient email address(es).
- **subject** (str): Email subject.
- **body** (str): Email body content.
- **cc** (Optional[Union[str, List[str]]]): CC recipient email address(es).
- **bcc** (Optional[Union[str, List[str]]]): BCC recipient email address(es).
- **attachments** (Optional[List[str]]): List of file paths to attach.
- **is_html** (bool): Whether the body is HTML format. Set to True when sending formatted emails with HTML tags (e.g., bold, links, images). Use False (default) for plain text emails.

**Returns:**

- **Dict[str, Any]**: A dictionary containing the result of the operation with keys:
  - `success` (bool): Whether the operation was successful
  - `message_id` (str): The ID of the sent message
  - `thread_id` (str): The ID of the email thread
  - `message` (str): Status message

**Example:**

```python
from camel.toolkits import GmailToolkit

gmail = GmailToolkit()
result = gmail.send_email(
    to="recipient@example.com",
    subject="Hello from CAMEL",
    body="This is a test email",
    cc=["cc@example.com"],
    attachments=["/path/to/file.pdf"],
    is_html=False
)
print(result)
# {'success': True, 'message_id': 'abc123', 'thread_id': 'abc123', 'message': 'Email sent successfully'}
```

<a id="camel.toolkits.gmail_toolkit.GmailToolkit.create_draft"></a>

### create_email_draft

```python
def create_email_draft(
    self,
    to: Union[str, List[str]],
    subject: str,
    body: str,
    cc: Optional[Union[str, List[str]]] = None,
    bcc: Optional[Union[str, List[str]]] = None,
    attachments: Optional[List[str]] = None,
    is_html: bool = False,
) -> Dict[str, Any]:
```

Create a draft email in Gmail.

**Parameters:**

- **to** (Union[str, List[str]]): Recipient email address(es).
- **subject** (str): Email subject.
- **body** (str): Email body content.
- **cc** (Optional[Union[str, List[str]]]): CC recipient email address(es).
- **bcc** (Optional[Union[str, List[str]]]): BCC recipient email address(es).
- **attachments** (Optional[List[str]]): List of file paths to attach.
- **is_html** (bool): Whether the body is HTML format.

**Returns:**

- **Dict[str, Any]**: A dictionary containing the result of the operation with keys:
  - `success` (bool): Whether the operation was successful
  - `draft_id` (str): The ID of the created draft
  - `message` (str): Status message

<a id="camel.toolkits.gmail_toolkit.GmailToolkit.get_messages"></a>

### fetch_emails

```python
def fetch_emails(
    self,
    query: str = "",
    max_results: int = 10,
    include_spam_trash: bool = False,
    label_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
```

Retrieve messages from Gmail.

**Parameters:**

- **query** (str): Gmail search query (e.g., "from:example@gmail.com", "subject:urgent"). (default: :obj:`""`)
- **max_results** (int): Maximum number of messages to retrieve. (default: :obj:`10`)
- **include_spam_trash** (bool): Whether to include messages from spam and trash. (default: :obj:`False`)
- **label_ids** (Optional[List[str]]): List of label IDs to filter by.

**Returns:**

- **Dict[str, Any]**: A dictionary containing the result of the operation with keys:
  - `success` (bool): Whether the operation was successful
  - `messages` (List[Dict]): List of message objects with metadata
  - `total_count` (int): Total number of messages found
  - `message` (str): Status message

**Example:**

```python
# Get recent messages
result = gmail.fetch_emails(max_results=5)

# Search for specific emails
result = gmail.fetch_emails(query="from:important@company.com", max_results=10)

# Get unread messages
result = gmail.fetch_emails(query="is:unread")
```

<a id="camel.toolkits.gmail_toolkit.GmailToolkit.get_message"></a>

### _get_message_details (internal)

```python
def _get_message_details(self, message_id: str) -> Optional[Dict[str, Any]]:
```

Get detailed fields for a message (subject, from, to, cc, bcc, date, body, attachments). Intended for internal use.

<a id="camel.toolkits.gmail_toolkit.GmailToolkit.get_attachments"></a>

### get_attachment

```python
def get_attachment(
    self,
    message_id: str,
    attachment_id: str,
    save_path: Optional[str] = None,
) -> Dict[str, Any]:
```

Retrieve attachments from a specific message.

**Parameters:**

- **message_id** (str): The ID of the message containing the attachment.
- **attachment_id** (str): The ID of the attachment to retrieve.
- **save_path** (Optional[str]): Path to save the attachment. If None, returns the attachment data.

**Returns:**

- **Dict[str, Any]**: A dictionary containing the result of the operation with keys:
  - `success` (bool): Whether the operation was successful
  - `attachment_data` (bytes): The attachment data (if save_path is None)
  - `saved_path` (str): The path where the attachment was saved (if save_path is provided)
  - `filename` (str): The name of the attachment file
  - `size` (int): The size of the attachment in bytes

<a id="camel.toolkits.gmail_toolkit.GmailToolkit.get_labels"></a>

### list_gmail_labels

```python
def list_gmail_labels(self) -> Dict[str, Any]:
```

Retrieve all labels from Gmail.

**Returns:**

- **Dict[str, Any]**: A dictionary containing the result of the operation with keys:
  - `success` (bool): Whether the operation was successful
  - `labels` (List[Dict]): List of label objects with metadata
  - `message` (str): Status message

<a id="camel.toolkits.gmail_toolkit.GmailToolkit.create_label"></a>

### create_label

```python
def create_label(
    self,
    name: str,
    message_list_visibility: str = "show",
    label_list_visibility: str = "labelShow",
) -> Dict[str, Any]:
```

Create a new label in Gmail.

**Parameters:**

- **name** (str): The name of the label to create.
- **message_list_visibility** (str): Visibility of the label in the message list. (default: :obj:`"show"`)
- **label_list_visibility** (str): Visibility of the label in the label list. (default: :obj:`"labelShow"`)

**Returns:**

- **Dict[str, Any]**: A dictionary containing the result of the operation with keys:
  - `success` (bool): Whether the operation was successful
  - `label_id` (str): The ID of the created label
  - `message` (str): Status message

<a id="camel.toolkits.gmail_toolkit.GmailToolkit.modify_message"></a>

### modify_email_labels

```python
def modify_email_labels(
    self,
    message_id: str,
    add_label_ids: Optional[List[str]] = None,
    remove_label_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
```

Modify labels of a specific message.

**Parameters:**

- **message_id** (str): The ID of the message to modify.
- **add_label_ids** (Optional[List[str]]): List of label IDs to add to the message.
- **remove_label_ids** (Optional[List[str]]): List of label IDs to remove from the message.

**Returns:**

- **Dict[str, Any]**: A dictionary containing the result of the operation with keys:
  - `success` (bool): Whether the operation was successful
  - `message_id` (str): The ID of the modified message
  - `message` (str): Status message

<a id="camel.toolkits.gmail_toolkit.GmailToolkit.delete_message"></a>

### move_to_trash

```python
def move_to_trash(self, message_id: str) -> Dict[str, Any]:
```

Delete a specific message.

**Parameters:**

- **message_id** (str): The ID of the message to delete.

**Returns:**

- **Dict[str, Any]**: A dictionary containing the result of the operation with keys:
  - `success` (bool): Whether the operation was successful
  - `message` (str): Status message

<a id="camel.toolkits.gmail_toolkit.GmailToolkit.get_contacts"></a>

### get_contacts

```python
def get_contacts(
    self,
    max_results: int = 100,
    page_size: int = 100,
) -> Dict[str, Any]:
```

Retrieve contacts from Google Contacts.

**Parameters:**

- **max_results** (int): Maximum number of contacts to retrieve. (default: :obj:`100`)
- **page_size** (int): Number of contacts per page. (default: :obj:`100`)

**Returns:**

- **Dict[str, Any]**: A dictionary containing the result of the operation with keys:
  - `success` (bool): Whether the operation was successful
  - `contacts` (List[Dict]): List of contact objects with metadata
  - `total_count` (int): Total number of contacts found
  - `message` (str): Status message

<a id="camel.toolkits.gmail_toolkit.GmailToolkit.search_contacts"></a>

### search_people

```python
def search_people(
    self,
    query: str,
    max_results: int = 10,
) -> Dict[str, Any]:
```

Search for contacts by name or email.

**Parameters:**

- **query** (str): Search query for contacts.
- **max_results** (int): Maximum number of contacts to retrieve. (default: :obj:`10`)

**Returns:**

- **Dict[str, Any]**: A dictionary containing the result of the operation with keys:
  - `success` (bool): Whether the operation was successful
  - `contacts` (List[Dict]): List of matching contact objects
  - `total_count` (int): Total number of contacts found
  - `message` (str): Status message

<a id="camel.toolkits.gmail_toolkit.GmailToolkit.get_user_profile"></a>

### get_profile

```python
def get_profile(self) -> Dict[str, Any]:
```

Retrieve the current user's Gmail profile information.

**Returns:**

- **Dict[str, Any]**: A dictionary containing the result of the operation with keys:
  - `success` (bool): Whether the operation was successful
  - `profile` (Dict): User profile information including email, name, etc.
  - `message` (str): Status message

<a id="camel.toolkits.gmail_toolkit.GmailToolkit.get_threads"></a>

### list_threads

```python
def list_threads(
    self,
    query: str = "",
    max_results: int = 10,
    include_spam_trash: bool = False,
    label_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
```

Retrieve email threads from Gmail.

**Parameters:**

- **query** (str): Gmail search query for threads. (default: :obj:`""`)
- **max_results** (int): Maximum number of threads to retrieve. (default: :obj:`10`)
- **include_spam_trash** (bool): Whether to include threads from spam and trash. (default: :obj:`False`)
- **label_ids** (Optional[List[str]]): List of label IDs to filter by.

**Returns:**

- **Dict[str, Any]**: A dictionary containing the result of the operation with keys:
  - `success` (bool): Whether the operation was successful
  - `threads` (List[Dict]): List of thread objects with metadata
  - `total_count` (int): Total number of threads found
  - `message` (str): Status message

<a id="camel.toolkits.gmail_toolkit.GmailToolkit.get_thread"></a>

### fetch_thread_by_id

```python
def fetch_thread_by_id(
    self,
    thread_id: str,
) -> Dict[str, Any]:
```

Retrieve a specific email thread by ID.

**Parameters:**

- **thread_id** (str): The ID of the thread to retrieve.
- **format** (Literal["minimal", "full", "metadata"]): The format of the thread to retrieve. (default: :obj:`"full"`)

**Returns:**

- **Dict[str, Any]**: A dictionary containing the result of the operation with keys:
  - `success` (bool): Whether the operation was successful
  - `thread` (Dict): The thread object with all messages
  - `thread_id` (str): The ID of the retrieved thread

<a id="camel.toolkits.gmail_toolkit.GmailToolkit.get_tools"></a>

### get_tools

```python
def get_tools(self) -> List[FunctionTool]:
```

Get all available Gmail tools as FunctionTool objects.

**Returns:**

- **List[FunctionTool]**: List of FunctionTool objects for all Gmail operations.

**Example:**

```python
from camel.toolkits import GmailToolkit
from camel.agents import ChatAgent

# Initialize Gmail toolkit
gmail_toolkit = GmailToolkit()

# Get all tools
tools = gmail_toolkit.get_tools()

# Create an agent with Gmail tools
agent = ChatAgent(
    system_message="You are a helpful Gmail assistant.",
    tools=tools
)

# Use the agent
response = agent.step("Send an email to john@example.com with subject 'Meeting' and body 'Let's meet tomorrow'")
```

## Usage Examples

### Basic Email Operations

```python
from camel.toolkits import GmailToolkit

# Initialize the toolkit
gmail = GmailToolkit()

# Send a simple email
result = gmail.send_email(
    to="recipient@example.com",
    subject="Hello from CAMEL",
    body="This is a test email sent using the CAMEL Gmail toolkit."
)

# Send an HTML email with attachments
result = gmail.send_email(
    to=["user1@example.com", "user2@example.com"],
    subject="Important Update",
    body="<h1>Important Update</h1><p>Please review the attached document.</p>",
    cc="manager@example.com",
    attachments=["/path/to/document.pdf"],
    is_html=True
)

# Create a draft
draft_result = gmail.create_draft(
    to="colleague@example.com",
    subject="Draft: Project Proposal",
    body="Here's the initial draft of our project proposal..."
)
```

### Message Management

```python
# Get recent messages
messages = gmail.fetch_emails(max_results=10)

# Search for specific emails
urgent_emails = gmail.fetch_emails(query="is:unread subject:urgent")

# Get messages from a specific sender
from_sender = gmail.fetch_emails(query="from:important@company.com")

# Get message details (internal helper)
message = gmail._get_message_details("message_id_here")

# Move a message to trash
delete_result = gmail.move_to_trash("message_id_here")
```

### Label Management

```python
# Get all labels
labels = gmail.list_gmail_labels()

# Create a new label
new_label = gmail.create_label("Important Projects")

# Modify message labels
gmail.modify_email_labels(
    message_id="message_id_here",
    add_label_ids=["label_id_here"],
    remove_label_ids=["INBOX"]
)
```

### Contact Management

```python
# Get all contacts
contacts = gmail.get_contacts()

# Search for specific contacts
search_results = gmail.search_contacts("John Smith")

# Get user profile
profile = gmail.get_profile()
```

### Thread Management

```python
# Get recent threads
threads = gmail.list_threads(max_results=5)

# Get a specific thread
thread = gmail.fetch_thread_by_id("thread_id_here")

# Search for threads
project_threads = gmail.get_threads(query="subject:project")
```

## Error Handling

All methods return a dictionary with a `success` boolean field. Check this field to determine if the operation was successful:

```python
result = gmail.send_email(
    to="invalid-email",
    subject="Test",
    body="Test message"
)

if result["success"]:
    print(f"Email sent successfully! Message ID: {result['message_id']}")
else:
    print(f"Failed to send email: {result['message']}")
```

## Authentication

The Gmail toolkit uses OAuth2 authentication with Google's Gmail API. This section covers the complete authentication setup and mechanisms.

### Prerequisites

Before using the Gmail toolkit, you need to set up Google API credentials:

1. **Google Cloud Console Setup:**
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Gmail API and Google People API
   - Create OAuth 2.0 credentials (Desktop application type)

2. **Download Credentials:**
   - Download the `credentials.json` file from the Google Cloud Console
   - Place it in your project directory or set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable

### Authentication Flow

The Gmail toolkit implements a multi-step OAuth2 authentication process:

#### 1. Initial Authentication
On first use, the toolkit will:

```python
# The authentication process happens automatically when initializing
gmail = GmailToolkit()  # This triggers the OAuth flow
```

**What happens behind the scenes:**
- Loads the `credentials.json` file
- Opens a browser window for user consent
- Requests permission for all required Gmail scopes
- Exchanges authorization code for access and refresh tokens
- Stores tokens securely in `token.json` for future use

#### 2. Token Storage
The toolkit stores authentication tokens in a local `token.json` file:

```json
{
  "token": "ya29.a0AfH6SMC...",
  "refresh_token": "1//04...",
  "token_uri": "https://oauth2.googleapis.com/token",
  "client_id": "your-client-id.apps.googleusercontent.com",
  "client_secret": "your-client-secret",
  "scopes": ["https://mail.google.com/", ...],
  "expiry": "2024-01-01T12:00:00Z"
}
```

#### 3. Automatic Token Refresh
The toolkit automatically handles token refresh:

- **Access tokens** expire after 1 hour
- **Refresh tokens** are used to obtain new access tokens
- **Automatic refresh** happens before each API call if needed
- **No user intervention** required after initial setup

### Required Scopes

The toolkit requests the following Gmail API scopes:

| Scope | Purpose | Access Level |
|-------|---------|--------------|
| `https://www.googleapis.com/auth/gmail.readonly` | Read emails and metadata | Read-only |
| `https://www.googleapis.com/auth/gmail.send` | Send emails | Write |
| `https://www.googleapis.com/auth/gmail.modify` | Modify emails and labels | Write |
| `https://www.googleapis.com/auth/gmail.compose` | Create drafts and compose | Write |
| `https://www.googleapis.com/auth/gmail.labels` | Manage labels | Write |
| `https://www.googleapis.com/auth/contacts.readonly` | Read Google Contacts | Read-only |
| `https://www.googleapis.com/auth/userinfo.profile` | Access user profile | Read-only |

### Environment Variables

You can configure authentication using environment variables:

```bash
# Set the path to your credentials file
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/credentials.json"

# Optional: Set custom token storage location
export GMAIL_TOKEN_PATH="/custom/path/token.json"
```

### Authentication Methods

#### Method 1: Credentials File (Recommended)
```python
# Place credentials.json in your project directory
gmail = GmailToolkit()
```

#### Method 2: Environment Variable
```python
import os
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/path/to/credentials.json'
gmail = GmailToolkit()
```

#### Method 3: Explicit Path
```python
# The toolkit will look for credentials.json in the current directory
# or use the path specified in GOOGLE_APPLICATION_CREDENTIALS
gmail = GmailToolkit()
```

### Troubleshooting Authentication

#### Common Issues and Solutions

**1. "Credentials not found" Error:**
```python
# Error: FileNotFoundError: [Errno 2] No such file or directory: 'credentials.json'
# Solution: Ensure credentials.json is in the correct location
```

**2. "Invalid credentials" Error:**
```python
# Error: google.auth.exceptions.RefreshError: The credentials do not contain the necessary fields
# Solution: Re-download credentials.json from Google Cloud Console
```

**3. "Access denied" Error:**
```python
# Error: googleapiclient.errors.HttpError: <HttpError 403 when requesting...>
# Solution: Check that Gmail API is enabled in Google Cloud Console
```

**4. "Token expired" Error:**
```python
# Error: google.auth.exceptions.RefreshError: The credentials have been revoked
# Solution: Delete token.json and re-authenticate
```

#### Debug Authentication Issues

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# This will show detailed authentication logs
gmail = GmailToolkit()
```

### Security Considerations

#### Token Security
- **Never commit** `token.json` to version control
- **Use environment variables** for production deployments
- **Rotate credentials** regularly in production
- **Limit scope** to only required permissions

#### Production Deployment
```python
# For production, use service account credentials
# or implement your own token management system
import os
from google.oauth2 import service_account

# Load service account credentials
credentials = service_account.Credentials.from_service_account_file(
    '/path/to/service-account.json',
    scopes=SCOPES
)

# Use with Gmail toolkit (requires additional implementation)
```

### Re-authentication

If you need to re-authenticate (e.g., after changing scopes):

```python
import os

# Delete the existing token file
if os.path.exists('token.json'):
    os.remove('token.json')

# Re-initialize the toolkit
gmail = GmailToolkit()  # This will trigger re-authentication
```

### Multi-User Support

For applications supporting multiple users:

```python
# Each user needs their own token file
user_id = "user123"
token_file = f"token_{user_id}.json"

# You would need to modify the toolkit to support custom token paths
# This is an advanced use case requiring custom implementation
```

### Best Practices

1. **Credential Management:**
   - Store credentials securely
   - Use environment variables in production
   - Implement proper error handling

2. **Token Handling:**
   - Monitor token expiration
   - Implement retry logic for token refresh
   - Log authentication events

3. **Scope Management:**
   - Request only necessary scopes
   - Regularly review and update permissions
   - Document scope requirements

4. **Error Handling:**
   - Handle authentication errors gracefully
   - Provide clear error messages to users
   - Implement fallback mechanisms

### Example: Complete Authentication Setup

```python
import os
from camel.toolkits import GmailToolkit

def setup_gmail_authentication():
    """Complete Gmail authentication setup."""
    
    # Check if credentials file exists
    if not os.path.exists('credentials.json'):
        raise FileNotFoundError(
            "credentials.json not found. Please download it from Google Cloud Console."
        )
    
    try:
        # Initialize Gmail toolkit (triggers authentication)
        gmail = GmailToolkit()
        print("✓ Gmail authentication successful!")
        return gmail
        
    except Exception as e:
        print(f"✗ Gmail authentication failed: {e}")
        print("Please check your credentials.json file and try again.")
        raise

# Usage
if __name__ == "__main__":
    gmail = setup_gmail_authentication()
    
    # Test authentication by getting user profile
    profile = gmail.get_user_profile()
    if profile['success']:
        print(f"Authenticated as: {profile['profile']['emailAddress']}")
    else:
        print("Authentication test failed")
```

This comprehensive authentication documentation covers all aspects of setting up and using the Gmail toolkit with proper security considerations and troubleshooting guidance.
