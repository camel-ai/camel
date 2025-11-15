from typing import Any, Optional

from tau2.utils import dump_file, get_pydantic_hash, load_file
from tau2.utils.pydantic_utils import BaseModelNoExtra


class DB(BaseModelNoExtra):
    """Domain database.

    This is a base class for all domain databases.
    """

    @classmethod
    def load(cls, path: str) -> "DB":
        """Load the database from a structured file like JSON, YAML, or TOML."""
        data = load_file(path)
        return cls.model_validate(data)

    def dump(self, path: str, exclude_defaults: bool = False, **kwargs: Any) -> None:
        """Dump the database to a file."""
        data = self.model_dump(exclude_defaults=exclude_defaults)
        dump_file(path, data, **kwargs)

    def get_json_schema(self) -> dict[str, Any]:
        """Get the JSON schema of the database."""
        return self.model_json_schema()

    def get_hash(self) -> str:
        """Get the hash of the database."""
        return get_pydantic_hash(self)

    def get_statistics(self) -> dict[str, Any]:
        """Get the statistics of the database."""
        return {}


def get_db_json_schema(db: Optional[DB] = None) -> dict[str, Any]:
    """Get the JSONschema of the database."""
    if db is None:
        return {}
    return db.get_json_schema()
