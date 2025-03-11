def collection_exists(client, collection_name: str) -> bool:
    """Check if a collection exists in the database."""
    for c in client.get_collections().collections:
        if collection_name == c.name:
            return True
    return False