from typing import Any, Dict, TypeVar

from addict import Dict as AddictDict
from pydantic import BaseModel, ConfigDict

from .utils import get_dict_hash

T = TypeVar("T", bound=BaseModel)


class BaseModelNoExtra(BaseModel):
    model_config = ConfigDict(extra="forbid")


def get_pydantic_hash(obj: BaseModel) -> str:
    """
    Generate a unique hash for the object based on its key fields.
    Returns a hex string representation of the hash.
    """
    hash_dict = obj.model_dump()
    return get_dict_hash(hash_dict)


def update_pydantic_model_with_dict(
    model_instance: T, update_data: Dict[str, Any]
) -> T:
    """
    Return an updated BaseModel instance based on the update_data.
    """
    raw_data = AddictDict(model_instance.model_dump())
    raw_data.update(AddictDict(update_data))
    new_data = raw_data.to_dict()
    model_class = type(model_instance)
    return model_class.model_validate(new_data)
