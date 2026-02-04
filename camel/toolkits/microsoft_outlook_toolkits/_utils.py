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

from typing import List, Optional


def _is_email_valid(email: str) -> bool:
    """Validates a single email address.
    Args:
        email (str): Email address to validate.
    Returns:
        bool: True if the email is valid, False otherwise.
    """
    import re
    from email.utils import parseaddr

    # Extract email address from both formats : "Email" , "Name <Email>"
    _, addr = parseaddr(email)

    email_pattern = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    return bool(addr and email_pattern.match(addr))


def _get_invalid_emails(*lists: Optional[List[str]]) -> List[str]:
    """Finds invalid email addresses from multiple email lists.
    Args:
        *lists: Variable number of optional email address lists.
    Returns:
        List[str]: List of invalid email addresses. Empty list if all
            emails are valid.
    """
    invalid_emails = []
    for email_list in lists:
        if email_list is None:
            continue
        for email in email_list:
            if not _is_email_valid(email):
                invalid_emails.append(email)
    return invalid_emails
