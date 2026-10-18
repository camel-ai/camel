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

import asyncio
import os
import time
from typing import Any, Dict, List, Optional

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.utils import MCPServer, api_keys_required

logger = get_logger(__name__)

# Global variables for bot instance management
_wechaty_bot = None
_bot_started = False


@MCPServer()
class WechatyToolkit(BaseToolkit):
    r"""A toolkit for WeChat operations using Wechaty framework.

    This toolkit provides methods to interact with WeChat through the
    Wechaty framework, supporting personal WeChat accounts for building
    conversational AI chatbots. The toolkit assumes WeChat is already
    logged in and ready for use by the agent.

    References:
        - Python Wechaty: https://github.com/Wechaty/python-wechaty/
        - Documentation: https://wechaty.readthedocs.io/zh_CN/latest/
        - Getting Started: https://github.com/Wechaty/python-wechaty/blob/main/README.md

    Notes:
        Requires 'wechaty' package: pip install wechaty
        Requires Wechaty token: Get free token from Wechaty community
        Token can be provided via parameter or WECHATY_TOKEN environment variable
        Bot automatically starts and maintains session for agent use
    """

    def __init__(self, timeout: Optional[float] = None, auto_start: bool = True, token: Optional[str] = None):
        r"""Initializes the WechatyToolkit for agent use.
        
        The toolkit requires a Wechaty token to connect to WeChat services.
        You can get a free token from Wechaty community or purchase a paid one.
        
        Args:
            timeout (Optional[float]): Request timeout in seconds.
            auto_start (bool): Whether to automatically establish WeChat 
                connection during initialization. (default: :obj:`True`)
            token (Optional[str]): Wechaty token for authentication. If not 
                provided, will try to get from environment variables.
        """
        super().__init__(timeout=timeout)
        self._import_wechaty_dependencies()
        self._bot_ready = False
        self._contacts_cache = {}
        self._rooms_cache = {}
        self._current_qr_code = None
        self._scan_status = None
        
        # Get token from parameter or environment
        # WECHATY_TOKEN is the standard environment variable name
        self._token = token or os.environ.get("WECHATY_TOKEN", "")
        
        if not self._token:
            raise ValueError(
                "Wechaty token is required. Please provide token parameter or set "
                "WECHATY_TOKEN environment variable. Get free token from: "
                "https://wechaty.js.org/zh/docs/specs/token"
            )
        
        # Auto-start bot if requested
        if auto_start:
            try:
                # Start bot in background thread to avoid blocking initialization
                import threading
                self._start_thread = threading.Thread(target=self._auto_start_bot)
                self._start_thread.daemon = True
                self._start_thread.start()
                logger.info("WeChat bot starting in background...")
            except Exception as e:
                logger.warning(f"Failed to auto-start bot: {e}")
                logger.info("You can manually start the bot using start_bot() method.")

    def _import_wechaty_dependencies(self):
        r"""Imports Wechaty dependencies with error handling."""
        try:
            # Import wechaty components
            global Wechaty, Contact, Room, Message, ScanStatus, EventType
            from wechaty import Wechaty, Contact, Room, Message
            from wechaty.user import Contact, Room, Message  
            from wechaty_puppet import ScanStatus, EventType
            logger.info("Wechaty dependencies imported successfully.")
        except ImportError as e:
            logger.error(f"Failed to import Wechaty: {e}")
            raise ImportError(
                "Wechaty not installed. Please install with: pip install wechaty"
            ) from e

    def _auto_start_bot(self):
        r"""Auto-starts the bot in a background thread."""
        try:
            # Run the async initialization in the thread
            asyncio.run(self._auto_initialize_bot())
        except Exception as e:
            logger.error(f"Error in auto-start bot thread: {e}")

    async def _auto_initialize_bot(self):
        r"""Async auto-initialization of the bot."""
        try:
            await self._initialize_bot()
            logger.info("WeChat bot auto-started successfully.")
        except Exception as e:
            logger.error(f"Failed to auto-initialize bot: {e}")

    async def _ensure_bot_ready(self, max_wait: int = 30) -> None:
        r"""Ensures the bot is ready, waiting if necessary."""
        if not self._bot_ready:
            await self._initialize_bot()
            
        # Wait for bot to be ready with timeout
        wait_time = 0
        while not self._bot_ready and wait_time < max_wait:
            await asyncio.sleep(1)
            wait_time += 1
            
        if not self._bot_ready:
            logger.warning(f"Bot not ready after {max_wait} seconds")

    async def _initialize_bot(self) -> None:
        r"""Initializes the Wechaty bot instance."""
        global _wechaty_bot, _bot_started
        
        if _wechaty_bot is None:
            from wechaty import Wechaty
            
            # Initialize bot with token
            _wechaty_bot = Wechaty(token=self._token)
            logger.info("Wechaty bot initialized with token")
            
            # Set up event handlers
            _wechaty_bot.on('scan', self._on_scan)
            _wechaty_bot.on('login', self._on_login)
            _wechaty_bot.on('logout', self._on_logout)
            _wechaty_bot.on('message', self._on_message)
            
        if not _bot_started:
            await _wechaty_bot.start()
            _bot_started = True
            # Wait for bot to be ready
            await asyncio.sleep(2)
            self._bot_ready = True

    async def _on_scan(self, qr_code: str, status: Any):
        r"""Handles QR code scanning event."""
        print("\n" + "="*60)
        print("WeChat Login Required")
        print("="*60)
        print(f"Please scan the QR code with your WeChat app:")
        print(f"QR Code URL: https://wechaty.js.org/qrcode/{qr_code}")
        print(f"Status: {status}")
        print("="*60 + "\n")
        
        logger.info(f"WeChat QR Code: https://wechaty.js.org/qrcode/{qr_code}")
        logger.info(f"Scan status: {status}")
        
        # Save QR code for later retrieval
        self._current_qr_code = qr_code
        self._scan_status = status

    async def _on_login(self, user: Any):
        r"""Handles login event."""
        logger.info(f"User {user} logged in")
        self._bot_ready = True

    async def _on_logout(self, user: Any):
        r"""Handles logout event."""
        logger.info(f"User {user} logged out")
        self._bot_ready = False

    async def _on_message(self, message: Any):
        r"""Handles incoming message event."""
        logger.info(f"Received message: {await message.text()}")

    def send_message(
        self,
        contact_name: str,
        message_text: str,
    ) -> str:
        r"""Sends a text message to a WeChat contact.

        This is the primary method for agents to send WeChat messages.
        The toolkit handles all connection management automatically.

        Args:
            contact_name (str): Name of the contact to send message to.
            message_text (str): Text content of the message.

        Returns:
            str: Success or error message.

        References:
            https://github.com/Wechaty/python-wechaty/blob/main/examples/
        """
        try:
            return asyncio.run(self._send_message_async(contact_name, message_text))
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return f"Failed to send message: {str(e)}"

    async def _send_message_async(self, contact_name: str, message_text: str) -> str:
        r"""Async implementation of send_message."""
        global _wechaty_bot
        
        await self._ensure_bot_ready()
        if not self._bot_ready:
            return "WeChat connection not available. Please ensure WeChat session is active."

        try:
            # Find contact by name
            contact = await _wechaty_bot.Contact.find(contact_name)
            if not contact:
                return f"Contact '{contact_name}' not found."

            # Send message
            await contact.say(message_text)
            logger.info(f"Message sent to {contact_name}: {message_text}")
            return f"Message sent successfully to {contact_name}."

        except Exception as e:
            logger.error(f"Error in _send_message_async: {e}")
            return f"Failed to send message: {str(e)}"

    def send_room_message(
        self,
        room_topic: str,
        message_text: str,
        mention_contact: Optional[str] = None,
    ) -> str:
        r"""Sends a message to a WeChat group room.

        Enables agents to communicate in WeChat group chats with optional
        user mentions for directed communication.

        Args:
            room_topic (str): Topic/name of the WeChat group room.
            message_text (str): Text content of the message.
            mention_contact (Optional[str]): Contact name to mention in the 
                message. (default: :obj:`None`)

        Returns:
            str: Success or error message.

        References:
            https://github.com/Wechaty/python-wechaty/blob/main/examples/
        """
        try:
            return asyncio.run(
                self._send_room_message_async(room_topic, message_text, mention_contact)
            )
        except Exception as e:
            logger.error(f"Error sending room message: {e}")
            return f"Failed to send room message: {str(e)}"

    async def _send_room_message_async(
        self, room_topic: str, message_text: str, mention_contact: Optional[str] = None
    ) -> str:
        r"""Async implementation of send_room_message."""
        global _wechaty_bot
        
        await self._ensure_bot_ready()
        if not self._bot_ready:
            return "WeChat connection not available. Please ensure WeChat session is active."

        try:
            # Find room by topic
            room = await _wechaty_bot.Room.find(room_topic)
            if not room:
                return f"Room '{room_topic}' not found."

            if mention_contact:
                # Find contact to mention
                contact = await _wechaty_bot.Contact.find(mention_contact)
                if contact:
                    await room.say(message_text, contact)
                    return f"Message sent to room '{room_topic}' mentioning {mention_contact}."
                else:
                    logger.warning(f"Contact '{mention_contact}' not found for mention")
                    await room.say(message_text)
            else:
                await room.say(message_text)

            logger.info(f"Message sent to room {room_topic}: {message_text}")
            return f"Message sent successfully to room '{room_topic}'."

        except Exception as e:
            logger.error(f"Error in _send_room_message_async: {e}")
            return f"Failed to send room message: {str(e)}"

    def get_contacts_list(self) -> Dict[str, Any]:
        r"""Retrieves list of WeChat contacts.

        Returns:
            Dict[str, Any]: Dictionary containing contacts information or 
                error information.

        References:
            https://github.com/Wechaty/python-wechaty/blob/main/examples/
        """
        try:
            return asyncio.run(self._get_contacts_list_async())
        except Exception as e:
            logger.error(f"Error getting contacts list: {e}")
            return {"error": f"Failed to get contacts list: {str(e)}"}

    async def _get_contacts_list_async(self) -> Dict[str, Any]:
        r"""Async implementation of get_contacts_list."""
        global _wechaty_bot
        
        await self._ensure_bot_ready()
        if not self._bot_ready:
            return {"error": "WeChat connection not available. Please ensure WeChat session is active."}

        try:
            contacts = await _wechaty_bot.Contact.find_all()
            contacts_info = []
            
            for contact in contacts:
                if await contact.type() == Contact.Type.Individual:
                    contact_info = {
                        "id": contact.contact_id,
                        "name": await contact.name(),
                        "alias": await contact.alias() or "",
                        "is_friend": await contact.friend(),
                    }
                    contacts_info.append(contact_info)

            logger.info(f"Retrieved {len(contacts_info)} contacts")
            return {
                "contacts": contacts_info,
                "total_count": len(contacts_info)
            }

        except Exception as e:
            logger.error(f"Error in _get_contacts_list_async: {e}")
            return {"error": f"Failed to get contacts list: {str(e)}"}

    def get_rooms_list(self) -> Dict[str, Any]:
        r"""Retrieves list of WeChat group rooms.

        Returns:
            Dict[str, Any]: Dictionary containing rooms information or 
                error information.

        References:
            https://github.com/Wechaty/python-wechaty/blob/main/examples/
        """
        try:
            return asyncio.run(self._get_rooms_list_async())
        except Exception as e:
            logger.error(f"Error getting rooms list: {e}")
            return {"error": f"Failed to get rooms list: {str(e)}"}

    async def _get_rooms_list_async(self) -> Dict[str, Any]:
        r"""Async implementation of get_rooms_list."""
        global _wechaty_bot
        
        await self._ensure_bot_ready()
        if not self._bot_ready:
            return {"error": "WeChat connection not available. Please ensure WeChat session is active."}

        try:
            rooms = await _wechaty_bot.Room.find_all()
            rooms_info = []
            
            for room in rooms:
                room_info = {
                    "id": room.room_id,
                    "topic": await room.topic(),
                    "member_count": len(await room.member_list()),
                }
                rooms_info.append(room_info)

            logger.info(f"Retrieved {len(rooms_info)} rooms")
            return {
                "rooms": rooms_info,
                "total_count": len(rooms_info)
            }

        except Exception as e:
            logger.error(f"Error in _get_rooms_list_async: {e}")
            return {"error": f"Failed to get rooms list: {str(e)}"}

    def get_bot_status(self) -> Dict[str, Any]:
        r"""Gets the current status of the Wechaty bot.

        Returns:
            Dict[str, Any]: Bot status information including login state,
                current user info, and connection status.

        References:
            https://github.com/Wechaty/python-wechaty/blob/main/examples/
        """
        try:
            return asyncio.run(self._get_bot_status_async())
        except Exception as e:
            logger.error(f"Error getting bot status: {e}")
            return {"error": f"Failed to get bot status: {str(e)}"}

    async def _get_bot_status_async(self) -> Dict[str, Any]:
        r"""Async implementation of get_bot_status."""
        global _wechaty_bot, _bot_started
        
        # Don't auto-initialize for status check, just report current state
        if _wechaty_bot is None:
            return {
                "bot_initialized": False,
                "bot_started": False,
                "logged_in": False,
                "user_info": None
            }

        try:
            user_self = _wechaty_bot.user_self()
            user_info = None
            
            if user_self:
                user_info = {
                    "id": user_self.contact_id,
                    "name": await user_self.name(),
                    "alias": await user_self.alias() or "",
                }

            return {
                "bot_initialized": True,
                "bot_started": _bot_started,
                "logged_in": self._bot_ready and user_self is not None,
                "user_info": user_info
            }

        except Exception as e:
            logger.error(f"Error in _get_bot_status_async: {e}")
            return {"error": f"Failed to get bot status: {str(e)}"}


    def send_file(
        self,
        contact_name: str,
        file_path: str,
    ) -> str:
        r"""Sends a file to a WeChat contact.

        Args:
            contact_name (str): Name of the contact to send file to.
            file_path (str): Path to the file to send.

        Returns:
            str: Success or error message.

        References:
            https://github.com/Wechaty/python-wechaty/blob/main/examples/
        """
        try:
            return asyncio.run(self._send_file_async(contact_name, file_path))
        except Exception as e:
            logger.error(f"Error sending file: {e}")
            return f"Failed to send file: {str(e)}"

    async def _send_file_async(self, contact_name: str, file_path: str) -> str:
        r"""Async implementation of send_file."""
        global _wechaty_bot
        
        await self._ensure_bot_ready()
        if not self._bot_ready:
            return "WeChat connection not available. Please ensure WeChat session is active."

        if not os.path.exists(file_path):
            return f"File not found: {file_path}"

        try:
            # Find contact by name
            contact = await _wechaty_bot.Contact.find(contact_name)
            if not contact:
                return f"Contact '{contact_name}' not found."

            # Create file box and send
            from wechaty import FileBox
            file_box = FileBox.from_file(file_path)
            await contact.say(file_box)
            
            logger.info(f"File sent to {contact_name}: {file_path}")
            return f"File sent successfully to {contact_name}."

        except Exception as e:
            logger.error(f"Error in _send_file_async: {e}")
            return f"Failed to send file: {str(e)}"

    def get_contact_info(self, contact_name: str) -> Dict[str, Any]:
        r"""Gets detailed information about a specific WeChat contact.

        Args:
            contact_name (str): Name of the contact to get information for.

        Returns:
            Dict[str, Any]: Contact information dictionary or error information.

        References:
            https://github.com/Wechaty/python-wechaty/blob/main/examples/
        """
        try:
            return asyncio.run(self._get_contact_info_async(contact_name))
        except Exception as e:
            logger.error(f"Error getting contact info: {e}")
            return {"error": f"Failed to get contact info: {str(e)}"}

    async def _get_contact_info_async(self, contact_name: str) -> Dict[str, Any]:
        r"""Async implementation of get_contact_info."""
        global _wechaty_bot
        
        await self._ensure_bot_ready()
        if not self._bot_ready:
            return {"error": "WeChat connection not available. Please ensure WeChat session is active."}

        try:
            # Find contact by name
            contact = await _wechaty_bot.Contact.find(contact_name)
            if not contact:
                return {"error": f"Contact '{contact_name}' not found."}

            contact_info = {
                "id": contact.contact_id,
                "name": await contact.name(),
                "alias": await contact.alias() or "",
                "is_friend": await contact.friend(),
                "gender": str(await contact.gender()),
                "province": await contact.province() or "",
                "city": await contact.city() or "",
                "avatar": await contact.avatar() or "",
            }

            logger.info(f"Retrieved contact info for {contact_name}")
            return contact_info

        except Exception as e:
            logger.error(f"Error in _get_contact_info_async: {e}")
            return {"error": f"Failed to get contact info: {str(e)}"}

    def get_room_info(self, room_topic: str) -> Dict[str, Any]:
        r"""Gets detailed information about a specific WeChat group room.

        Args:
            room_topic (str): Topic/name of the WeChat group room.

        Returns:
            Dict[str, Any]: Room information dictionary or error information.

        References:
            https://github.com/Wechaty/python-wechaty/blob/main/examples/
        """
        try:
            return asyncio.run(self._get_room_info_async(room_topic))
        except Exception as e:
            logger.error(f"Error getting room info: {e}")
            return {"error": f"Failed to get room info: {str(e)}"}

    async def _get_room_info_async(self, room_topic: str) -> Dict[str, Any]:
        r"""Async implementation of get_room_info."""
        global _wechaty_bot
        
        await self._ensure_bot_ready()
        if not self._bot_ready:
            return {"error": "WeChat connection not available. Please ensure WeChat session is active."}

        try:
            # Find room by topic
            room = await _wechaty_bot.Room.find(room_topic)
            if not room:
                return {"error": f"Room '{room_topic}' not found."}

            members = await room.member_list()
            member_info = []
            for member in members:
                member_info.append({
                    "name": await member.name(),
                    "alias": await member.alias() or "",
                })

            room_info = {
                "id": room.room_id,
                "topic": await room.topic(),
                "member_count": len(members),
                "members": member_info,
                "owner": await room.owner(),
            }

            logger.info(f"Retrieved room info for {room_topic}")
            return room_info

        except Exception as e:
            logger.error(f"Error in _get_room_info_async: {e}")
            return {"error": f"Failed to get room info: {str(e)}"}


    def get_tools(self) -> List[FunctionTool]:
        r"""Returns toolkit functions as tools."""
        return [
            FunctionTool(self.send_message),
            FunctionTool(self.send_room_message),
            FunctionTool(self.send_file),
            FunctionTool(self.get_contacts_list),
            FunctionTool(self.get_rooms_list),
            FunctionTool(self.get_contact_info),
            FunctionTool(self.get_room_info),
        ]
