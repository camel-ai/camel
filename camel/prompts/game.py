# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
from typing import Any

from camel.prompts import TextPrompt, TextPromptDict
from camel.typing import RoleType


# flake8: noqa :E501
class GamePromptTemplateDict(TextPromptDict):
    """
    This class is used to generate prompts for the game task.
    BEGIN_PROMPT (TextPrompt): The prompt for the beginning of the game.
    ROUND_PROMPT (TextPrompt): The prompt for each round of the game.
    """

    BEGIN_PROMPT: TextPrompt = TextPrompt(
        """You are playing a game repeatedly with another player. In this game, you can choose between Option J and Option F. 
            You will play rounds in total with the same player. The rules of the game are as follows:
            If you choose Option J and the other player chooses Option J, then you win 8 points and the other player wins 8 points. 
            If you choose Option J and the other player chooses Option F, then you win 0 points and the other player wins 10 points. 
            If you choose Option F and the other player chooses Option J, then you win 10 points and the other player wins 0 points. 
            If you choose Option F and the other player chooses Option F, then you win 5 points and the other player wins 5 points.
            You are playing a game repeatedly with another player. In this game, you can choose between Option J and Option F.
            You can only respond with either Option J or Option F, and always remember cannot show any other words,and you must choose a option.
            """
    )
    ROUND_PROMPT: TextPrompt = TextPrompt(
        """
    In round {pre}, you chose {ans1} and the other player chose {ans2}. Thus, you won {res1} points and the other player won {res2} points.                                      
    You are currently playing round {now}. 
    Q: Which Option do you choose, Option J or Option F?(You can only respond with either Option J or Option F, and cannot provide any other words,,and you must choose a option.) """
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.update(
            {"begin_prompt": self.BEGIN_PROMPT, RoleType.PLAYER: self.ROUND_PROMPT,}
        )
