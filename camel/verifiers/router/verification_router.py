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
"""Verifier module for routing to domain-specific verifiers."""

from typing import Any, ClassVar, Dict, Optional, Type, Union

from datasets import Dataset

from camel.verifiers.base_verifier import BaseVerifier
from camel.verifiers.math_verifier import MathVerifier


class DomainVerifier:
    """Main verifier class that routes to domain-specific verifiers."""

    VERIFIERS: ClassVar[Dict[str, Type[BaseVerifier]]] = {
        "math": MathVerifier,
    }

    @classmethod
    def verify(
        cls,
        domain: str,
        data: Union[Dataset, Dict[str, Any]],
        criteria: Optional[Dict[str, Any]] = None,
    ) -> Dataset:
        """Verify data using appropriate domain-specific verifier.

        Args:
            domain: Domain identifier ("math", "code", etc)
            data: Data to verify (Dataset or dict)
            criteria: Optional verification criteria

        Returns:
            Verified dataset with results

        Raises:
            ValueError: If domain is not supported and strict_mode is True
        """
        # Convert dict to dataset if needed
        if isinstance(data, dict):
            data = Dataset.from_dict(data)

        # Get appropriate verifier
        verifier_cls = cls.VERIFIERS.get(domain)
        if verifier_cls is None:
            if criteria and criteria.get("strict_mode", False):
                raise ValueError(f"Unsupported domain: {domain}")
            # Default to marking everything as correct if no specific verifier
            return data.add_column("correct", [True] * len(data))

        # Create verifier instance and verify
        verifier = verifier_cls(criteria=criteria)
        verified_data = verifier.verify(data)

        # Filter to only correct results if specified
        if criteria and criteria.get("filter_incorrect", False):
            verified_data = verified_data.filter(lambda x: x["correct"])

        return verified_data

    @classmethod
    def get_supported_domains(cls) -> list[str]:
        """Get list of supported verification domains.

        Returns:
            List of domain identifiers that have registered verifiers
        """
        return list(cls.VERIFIERS.keys())

    @classmethod
    def register_verifier(
        cls, domain: str, verifier_cls: Type[BaseVerifier]
    ) -> None:
        """Register a new domain verifier.

        Args:
            domain: Domain identifier
            verifier_cls: Verifier class to register

        Raises:
            ValueError: If domain is already registered
        """
        if domain in cls.VERIFIERS:
            raise ValueError(
                f"Domain {domain} already has a registered verifier"
            )
        cls.VERIFIERS[domain] = verifier_cls
