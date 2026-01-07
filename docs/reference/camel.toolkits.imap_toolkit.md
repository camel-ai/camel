<a id="camel.toolkits.imap_mail_toolkit"></a>


## IMAPMailToolkit

```python
class IMAPMailToolkit(BaseToolkit):
```

A toolkit for IMAP email operations.

This toolkit provides comprehensive email functionality including fetching emails with filtering options, retrieving specific emails by ID, sending emails via SMTP, replying to emails, moving emails to folders, and deleting emails. The toolkit implements connection pooling with automatic idle timeout to prevent resource leaks when used by LLM agents.

<a id="camel.toolkits.imap_mail_toolkit.IMAPMailToolkit.__init__"></a>

### **init**

```python
def __init__(
    self,
    imap_server: Optional[str] = None,
    imap_port: int = 993,
    smtp_server: Optional[str] = None,
    smtp_port: int = 587,
    username: Optional[str] = None,
    password: Optional[str] = None,
    timeout: Optional[float] = None,
    connection_idle_timeout: float = 300.0,
):
```

Initialize the IMAP Mail Toolkit.

**Parameters:**

- **imap_server** (str, optional): IMAP server hostname. If not provided, will be obtained from environment variable `IMAP_SERVER`.
- **imap_port** (int, optional): IMAP server port. Defaults to `993`.
- **smtp_server** (str, optional): SMTP server hostname. If not provided, will be obtained from environment variable `SMTP_SERVER`.
- **smtp_port** (int, optional): SMTP server port. Defaults to `587`.
- **username** (str, optional): Email username. If not provided, will be obtained from environment variable `EMAIL_USERNAME`.
- **password** (str, optional): Email password. If not provided, will be obtained from environment variable `EMAIL_PASSWORD`.
- **timeout** (Optional[float]): The timeout for the toolkit operations. Defaults to `None`.
- **connection_idle_timeout** (float): Maximum idle time (in seconds) before auto-closing connections. Defaults to `300.0` (5 minutes).

<a id="camel.toolkits.imap_mail_toolkit.IMAPMailToolkit.fetch_emails"></a>

### fetch_emails

```python
def fetch_emails(
    self,
    folder: Literal["INBOX"] = "INBOX",
    limit: int = 10,
    unread_only: bool = False,
    sender_filter: Optional[str] = None,
    subject_filter: Optional[str] = None,
):
```

Fetch emails from a folder with optional filtering.

**Parameters:**

- **folder** (Literal["INBOX"]): Email folder to search in. Defaults to `"INBOX"`.
- **limit** (int): Maximum number of emails to retrieve. Defaults to `10`.
- **unread_only** (bool): If True, only fetch unread emails. Defaults to `False`.
- **sender_filter** (str, optional): Filter emails by sender email address. Defaults to `None`.
- **subject_filter** (str, optional): Filter emails by subject content. Defaults to `None`.

**Returns:**

List[Dict]: List of email dictionaries with metadata including id, subject, from, to, date, size, and body.

<a id="camel.toolkits.imap_mail_toolkit.IMAPMailToolkit.get_email_by_id"></a>

### get_email_by_id

```python
def get_email_by_id(
    self,
    email_id: str,
    folder: Literal["INBOX"] = "INBOX",
):
```

Retrieve a specific email by ID with full metadata.

**Parameters:**

- **email_id** (str): ID of the email to retrieve.
- **folder** (Literal["INBOX"]): Folder containing the email. Defaults to `"INBOX"`.

**Returns:**

Dict: Email dictionary with complete metadata including id, subject, from, to, cc, bcc, date, message_id, reply_to, in_reply_to, references, priority, size, and body.

<a id="camel.toolkits.imap_mail_toolkit.IMAPMailToolkit.send_email"></a>

### send_email

```python
def send_email(
    self,
    to_recipients: List[str],
    subject: str,
    body: str,
    cc_recipients: Optional[List[str]] = None,
    bcc_recipients: Optional[List[str]] = None,
    html_body: Optional[str] = None,
):
```

Send an email via SMTP.

**Parameters:**

- **to_recipients** (List[str]): List of recipient email addresses.
- **subject** (str): Email subject line.
- **body** (str): Plain text email body.
- **cc_recipients** (List[str], optional): List of CC recipient email addresses. Defaults to `None`.
- **bcc_recipients** (List[str], optional): List of BCC recipient email addresses. Defaults to `None`.
- **html_body** (str, optional): HTML version of email body. Defaults to `None`.

**Returns:**

str: Success message indicating the email was sent successfully.

<a id="camel.toolkits.imap_mail_toolkit.IMAPMailToolkit.reply_to_email"></a>

### reply_to_email

```python
def reply_to_email(
    self,
    original_email_id: str,
    reply_body: str,
    folder: Literal["INBOX"] = "INBOX",
    html_body: Optional[str] = None,
):
```

Send a reply to an existing email.

**Parameters:**

- **original_email_id** (str): ID of the email to reply to.
- **reply_body** (str): Reply message body.
- **folder** (Literal["INBOX"]): Folder containing the original email. Defaults to `"INBOX"`.
- **html_body** (str, optional): HTML version of reply body. Defaults to `None`.

**Returns:**

str: Success message indicating the reply was sent successfully.

<a id="camel.toolkits.imap_mail_toolkit.IMAPMailToolkit.move_email_to_folder"></a>

### move_email_to_folder

```python
def move_email_to_folder(
    self,
    email_id: str,
    target_folder: str,
    source_folder: Literal["INBOX"] = "INBOX",
):
```

Move an email to a different folder.

**Parameters:**

- **email_id** (str): ID of the email to move.
- **target_folder** (str): Destination folder name.
- **source_folder** (Literal["INBOX"]): Source folder name. Defaults to `"INBOX"`.

**Returns:**

str: Success message indicating the email was moved successfully.

<a id="camel.toolkits.imap_mail_toolkit.IMAPMailToolkit.delete_email"></a>

### delete_email

```python
def delete_email(
    self,
    email_id: str,
    folder: Literal["INBOX"] = "INBOX",
    permanent: bool = False,
):
```

Delete an email.

**Parameters:**

- **email_id** (str): ID of the email to delete.
- **folder** (Literal["INBOX"]): Folder containing the email. Defaults to `"INBOX"`.
- **permanent** (bool): If True, permanently delete the email. If False, move to trash (soft delete). Defaults to `False`.

**Returns:**

str: Success message indicating the email was deleted or moved to trash.

<a id="camel.toolkits.imap_mail_toolkit.IMAPMailToolkit.close"></a>

### close

```python
def close(self):
```

Close all open connections.

This method should be called when the toolkit is no longer needed to properly clean up network connections.

<a id="camel.toolkits.imap_mail_toolkit.IMAPMailToolkit.get_tools"></a>

### get_tools

```python
def get_tools(self):
```

Get list of tools provided by this toolkit.

**Returns:**

List[FunctionTool]: A list of FunctionTool objects representing the functions in the toolkit (fetch_emails, get_email_by_id, send_email, reply_to_email, move_email_to_folder, delete_email).
