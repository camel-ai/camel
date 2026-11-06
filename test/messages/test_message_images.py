# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
import base64
import io

from PIL import Image

from camel.messages import BaseMessage


def test_to_openai_user_message_keeps_image_format_untouched():
    r"""Converting a message must not mutate the caller's PIL image, so the
    same image can be encoded again with its original format."""
    image = Image.new('RGB', (8, 8), 'red')
    assert image.format is None

    message = BaseMessage.make_user_message(
        role_name='user', content='what is this?', image_list=[image]
    )
    openai_message = message.to_openai_user_message()

    assert image.format is None
    url = openai_message['content'][1]['image_url']['url']
    assert url.startswith('data:image/png;base64,')
    assert len(base64.b64decode(url.split(',', 1)[1])) > 0


def test_to_openai_user_message_respects_existing_image_format():
    r"""A JPEG image keeps being encoded as JPEG."""
    buffer = io.BytesIO()
    Image.new('RGB', (8, 8), 'blue').save(buffer, format='JPEG')
    buffer.seek(0)
    image = Image.open(buffer)
    assert image.format == 'JPEG'

    message = BaseMessage.make_user_message(
        role_name='user', content='what is this?', image_list=[image]
    )
    openai_message = message.to_openai_user_message()

    assert image.format == 'JPEG'
    url = openai_message['content'][1]['image_url']['url']
    assert url.startswith('data:image/jpeg;base64,')
