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

"""
USDCtoFiat Toolkit — USDC to fiat cash-out on Base

USDCtoFiat by Galleon Labs. Built on the public Peer/ZKP2P protocol.
Docs: https://usdctofiat.xyz/developers

UsdctoFiatToolkit is a CAMEL BaseToolkit. mode is required on cashout
and estimate: "fast" (0% / TOFIAT) or "best" (Delegate, 10 bps).
There is no default.

The toolkit does not accept a wallet private key. Inject a signer
callback that submits unsigned {to, data, value, chainId} txs, or omit
the signer and usdctofiat_cashout() returns the unsigned prepare
payload for the host to sign.

Install: ``pip install camel-ai[usdctofiat]`` or ``pip install usdctofiat``.
"""

# from camel.agents import ChatAgent
# from camel.models import ModelFactory
from camel.toolkits import UsdctoFiatToolkit

# from camel.types import ModelPlatformType, ModelType


def signer(tx):
    # Host signs and submits {to, data, value, chainId}. Return the tx
    # hash. Keep the key in *your* runtime. Never pass it to
    # UsdctoFiatToolkit.
    raise NotImplementedError("inject your wallet signer")


toolkit = UsdctoFiatToolkit(signer=signer)

# model = ModelFactory.create(
#     model_platform=ModelPlatformType.OPENAI,
#     model_type=ModelType.GPT_4O_MINI,
# )
# agent = ChatAgent(
#     system_message=(
#         "You help users cash out Base USDC to fiat via USDCtoFiat by "
#         "Galleon Labs. Built on the public Peer/ZKP2P protocol. "
#         "Always ask the user to choose mode=fast "
#         "(0% / TOFIAT) or mode=best (Delegate, 10 bps). Never invent a "
#         "mode default. Never ask for a wallet private key."
#     ),
#     model=model,
#     tools=toolkit.get_tools(),
# )

if __name__ == "__main__":
    print(
        toolkit.usdctofiat_estimate(mode="fast", amount="100", currency="EUR")
    )
