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

import logging
from itertools import cycle
from random import choice
from typing import Any, Dict, List, Optional, Union

from camel.models.base_model import BaseModelBackend

logger = logging.getLogger(__name__)


class ModelManager:
    r"""ModelManager choosing a model from provided list.
    Models are picked according to defined strategy.

    Args:
        models(Union[BaseModelBackend, List[BaseModelBackend]]):
            model backend or list of model backends
            (e.g., model instances, APIs)
        scheduling_strategy (str): name of function that defines how to select
            the next model.
            (default: :str:`round_robin`)
    """

    def __init__(
        self,
        models: Union[BaseModelBackend, List[BaseModelBackend]],
        scheduling_strategy: str = "round_robin",
    ):
        if isinstance(models, list):
            self.models = models
        else:
            self.models = [models]
        self.models_cycle = cycle(self.models)
        self.current_model = self.models[0]

        # Set the scheduling strategy; default is round-robin
        try:
            self.scheduling_strategy = getattr(self, scheduling_strategy)
        except AttributeError:
            logger.warning(
                f"Provided strategy: {scheduling_strategy} is not implemented."
                f"Using default 'round robin'"
            )
            self.scheduling_strategy = self.round_robin

    @property
    def model_type(self):
        """Return type of the current model."""
        return self.current_model.model_type

    @property
    def model_config_dict(self):
        """Return model_config_dict of the current model."""
        return self.current_model.model_config_dict

    @model_config_dict.setter
    def model_config_dict(self, model_config_dict: Dict[str, Any]):
        """Set model_config_dict to the current model."""
        self.current_model.model_config_dict = model_config_dict

    @property
    def current_model_index(self) -> Optional[int]:
        """Return the index of current model in self.models list."""
        return self.models.index(self.current_model)

    @property
    def token_limit(self):
        """Return token_limit of the current model."""
        return self.current_model.token_limit

    @property
    def token_counter(self):
        """Return token_counter of the current model."""
        return self.current_model.token_counter

    # Strategies
    def round_robin(self) -> BaseModelBackend:
        """Return models one by one in simple round-robin fashion."""
        return next(self.models_cycle)

    def always_first(self) -> BaseModelBackend:
        """Always returns the first model from self.models."""
        return self.models[0]

    def random_model(self) -> BaseModelBackend:
        """Return random model from self.models list."""
        return choice(self.models)

    def run(self, messages):
        """
        Process a list of messages by selecting a model based on
        the scheduling strategy.
        Sends the entire list of messages to the selected model,
        and returns a single response.
        messages: List of lists of messages to be processed.
        """
        self.current_model = self.scheduling_strategy()

        # Pass all messages to the selected model and get the response
        try:
            response = self.current_model.run(messages)
        except Exception as exc:
            if self.scheduling_strategy == self.always_first:
                self.scheduling_strategy = self.round_robin
                # Skip already used one
                self.current_model = self.scheduling_strategy()
            raise exc
        return response
