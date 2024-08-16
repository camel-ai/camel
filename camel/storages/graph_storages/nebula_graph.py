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
import os
from hashlib import md5
from typing import Any, Dict, List, Optional

from camel.storages.graph_storages import BaseGraphStorage, GraphElement
from camel.utils import dependencies_required
from string import Template


QUOTE = '"'
RETRY_TIMES = 3
WAIT_MIN_SECONDS = 0.5
WAIT_MAX_SECONDS = 10


logger = logging.getLogger(__name__)


rel_query_sample_edge = Template(
    """
MATCH ()-[e:`$edge_type`]->()
RETURN [src(e), dst(e)] AS sample_edge LIMIT 1
"""
)

rel_query_edge_type = Template(
    """
MATCH (m)-[:`$edge_type`]->(n)
  WHERE id(m) == $quote$src_id$quote AND id(n) == $quote$dst_id$quote
RETURN "(:" + tags(m)[0] + ")-[:$edge_type]->(:" + tags(n)[0] + ")" AS rels
"""
)

def hash_string_to_rank(string: str) -> int:
    # get signed 64-bit hash value
    signed_hash = hash(string)

    # reduce the hash value to a 64-bit range
    mask = (1 << 64) - 1
    signed_hash &= mask

    # convert the signed hash value to an unsigned 64-bit integer
    if signed_hash & (1 << 63):
        unsigned_hash = -((signed_hash ^ mask) + 1)
    else:
        unsigned_hash = signed_hash

    return unsigned_hash


class NebulaGraphStore(BaseGraphStorage):
    """NebulaGraph graph store."""

    @dependencies_required('nebula3')
    def __init__(
        self,
        session_pool: Optional[Any] = None,
        space_name: Optional[str] = None,
        edge_types: Optional[List[str]] = ["relationship"],
        rel_prop_names: Optional[List[str]] = ["relationship,"],
        tags: Optional[List[str]] = ["entity"],
        tag_prop_names: Optional[List[str]] = ["name,"],
        include_vid: bool = True,
        session_pool_kwargs: Optional[Dict[str, Any]] = {},
        **kwargs: Any,
    ) -> None:
        """Initialize NebulaGraph graph store.

        Args:
            session_pool: NebulaGraph session pool.
            space_name: NebulaGraph space name.
            edge_types: Edge types.
            rel_prop_names: Relation property names corresponding to edge types.
            tags: Tags.
            tag_prop_names: Tag property names corresponding to tags.
            session_pool_kwargs: Keyword arguments for NebulaGraph session pool.
            **kwargs: Keyword arguments.
        """

        import nebula3

        assert space_name is not None, "space_name should be provided."
        self._space_name = space_name
        self._session_pool_kwargs = session_pool_kwargs

        self._session_pool: Any = session_pool
        if self._session_pool is None:
            self.init_session_pool()

        self._vid_type = self._get_vid_type()

        self._tags = tags or ["entity"]
        self._edge_types = edge_types or ["rel"]
        self._rel_prop_names = rel_prop_names or ["predicate,"]
        if len(self._edge_types) != len(self._rel_prop_names):
            raise ValueError(
                "edge_types and rel_prop_names to define relation and relation name"
                "should be provided, yet with same length."
            )
        if len(self._edge_types) == 0:
            raise ValueError("Length of `edge_types` should be greater than 0.")

        if tag_prop_names is None or len(self._tags) != len(tag_prop_names):
            raise ValueError(
                "tag_prop_names to define tag and tag property name should be "
                "provided, yet with same length."
            )

        if len(self._tags) == 0:
            raise ValueError("Length of `tags` should be greater than 0.")

        # for building query
        self._edge_dot_rel = [
            f"`{edge_type}`.`{rel_prop_name}`"
            for edge_type, rel_prop_name in zip(self._edge_types, self._rel_prop_names)
        ]

        self._edge_prop_map = {}
        for edge_type, rel_prop_name in zip(self._edge_types, self._rel_prop_names):
            self._edge_prop_map[edge_type] = [
                prop.strip() for prop in rel_prop_name.split(",")
            ]

        # cypher string like: map{`follow`: "degree", `serve`: "start_year,end_year"}
        self._edge_prop_map_cypher_string = (
            "map{"
            + ", ".join(
                [
                    f"`{edge_type}`: \"{','.join(rel_prop_names)}\""
                    for edge_type, rel_prop_names in self._edge_prop_map.items()
                ]
            )
            + "}"
        )

        # build tag_prop_names map
        self._tag_prop_names_map = {}
        for tag, prop_names in zip(self._tags, tag_prop_names or []):
            if prop_names is not None:
                self._tag_prop_names_map[tag] = f"`{tag}`.`{prop_names}`"
        self._tag_prop_names: List[str] = list(
            {
                prop_name.strip()
                for prop_names in tag_prop_names or []
                if prop_names is not None
                for prop_name in prop_names.split(",")
            }
        )

        self._include_vid = include_vid

    def init_session_pool(self) -> Any:
        """Return NebulaGraph session pool."""
        from nebula3.Config import SessionPoolConfig
        from nebula3.gclient.net.SessionPool import SessionPool

        # ensure "NEBULA_USER", "NEBULA_PASSWORD", "NEBULA_ADDRESS" are set
        # in environment variables
        if not all(
                key in os.environ
                for key in ["NEBULA_USER", "NEBULA_PASSWORD", "NEBULA_ADDRESS"]
        ):
            raise ValueError(
                "NEBULA_USER, NEBULA_PASSWORD, NEBULA_ADDRESS should be set in "
                "environment variables when NebulaGraph Session Pool is not "
                "directly passed."
            )
        graphd_host, graphd_port = os.environ["NEBULA_ADDRESS"].split(":")
        session_pool = SessionPool(
            os.environ["NEBULA_USER"],
            os.environ["NEBULA_PASSWORD"],
            self._space_name,
            [(graphd_host, int(graphd_port))],
        )

        seesion_pool_config = SessionPoolConfig()
        session_pool.init(seesion_pool_config)
        self._session_pool = session_pool
        return self._session_pool

    def __del__(self) -> None:
        """Close NebulaGraph session pool."""
        self._session_pool.close()

    @property
    def get_client(self) -> Any:
        """Return NebulaGraph session pool."""
        return self._session_pool
    @property
    def get_schema(self, refresh: bool = False) -> str:
        """Get the schema of the NebulaGraph store."""
        if self.schema and not refresh:
            return self.schema
        self.refresh_schema()
        logger.debug(f"get_schema()\nschema: {self.schema}")
        return self.schema

    def execute(self, query: str, param_map: Optional[Dict[str, Any]] = {}) -> Any:
        """Execute query.

        Args:
            query: Query.
            param_map: Parameter map.

        Returns:
            Query result.
        """
        from nebula3.Exception import IOErrorException
        from nebula3.fbthrift.transport.TTransport import TTransportException

        # Clean the query string by removing triple backticks
        query = query.replace("```", "").strip()

        try:
            result = self._session_pool.execute_parameter(query, param_map)
            if result is None:
                raise ValueError(f"Query failed. Query: {query}, Param: {param_map}")
            if not result.is_succeeded():
                raise ValueError(
                    f"Query failed. Query: {query}, Param: {param_map}"
                    f"Error message: {result.error_msg()}"
                )
            return result
        except (TTransportException, IOErrorException, RuntimeError) as e:
            logger.error(
                f"Connection issue, try to recreate session pool. Query: {query}, "
                f"Param: {param_map}"
                f"Error: {e}"
            )
            self.init_session_pool()
            logger.info(
                f"Session pool recreated. Query: {query}, Param: {param_map}"
                f"This was due to error: {e}, and now retrying."
            )
            raise

        except ValueError as e:
            # query failed on db side
            logger.error(
                f"Query failed. Query: {query}, Param: {param_map}"
                f"Error message: {e}"
            )
            raise
        except Exception as e:
            # other exceptions
            logger.error(
                f"Query failed. Query: {query}, Param: {param_map}"
                f"Error message: {e}"
            )
            raise

    def query(self, query: str, param_map: Optional[Dict[str, Any]] = {}) -> Any:
            result = self.execute(query, param_map)
            columns = result.keys()
            d: Dict[str, list] = {}
            for col_num in range(result.col_size()):
                col_name = columns[col_num]
                col_list = result.column_values(col_name)
                d[col_name] = [x.cast() for x in col_list]
            return d

    @property
    def refresh_schema(self) -> None:
        """
        Refreshes the NebulaGraph Store Schema.
        """
        tags_schema, edge_types_schema, relationships = [], [], []
        for tag in self.execute("SHOW TAGS").column_values("Name"):
            tag_name = tag.cast()
            tag_schema = {"tag": tag_name, "properties": []}
            r = self.execute(f"DESCRIBE TAG `{tag_name}`")
            props, types, comments = (
                r.column_values("Field"),
                r.column_values("Type"),
                r.column_values("Comment"),
            )
            for i in range(r.row_size()):
                # back compatible with old version of nebula-python
                property_defination = (
                    (props[i].cast(), types[i].cast())
                    if comments[i].is_empty()
                    else (props[i].cast(), types[i].cast(), comments[i].cast())
                )
                tag_schema["properties"].append(property_defination)
            tags_schema.append(tag_schema)
        for edge_type in self.execute("SHOW EDGES").column_values("Name"):
            edge_type_name = edge_type.cast()
            edge_schema = {"edge": edge_type_name, "properties": []}
            r = self.execute(f"DESCRIBE EDGE `{edge_type_name}`")
            props, types, comments = (
                r.column_values("Field"),
                r.column_values("Type"),
                r.column_values("Comment"),
            )
            for i in range(r.row_size()):
                # back compatible with old version of nebula-python
                property_defination = (
                    (props[i].cast(), types[i].cast())
                    if comments[i].is_empty()
                    else (props[i].cast(), types[i].cast(), comments[i].cast())
                )
                edge_schema["properties"].append(property_defination)
            edge_types_schema.append(edge_schema)

            # build relationships types
            sample_edge = self.execute(
                rel_query_sample_edge.substitute(edge_type=edge_type_name)
            ).column_values("sample_edge")
            if len(sample_edge) == 0:
                continue
            src_id, dst_id = sample_edge[0].cast()
            r = self.execute(
                rel_query_edge_type.substitute(
                    edge_type=edge_type_name,
                    src_id=src_id,
                    dst_id=dst_id,
                    quote="" if self._vid_type == "INT64" else QUOTE,
                )
            ).column_values("rels")
            if len(r) > 0:
                relationships.append(r[0].cast())

        self.schema = (
            f"Node properties: {tags_schema}\n"
            f"Edge properties: {edge_types_schema}\n"
            f"Relationships: {relationships}\n"
        )


    @property
    def add_triplet(self, subj: str, rel: str, obj: str) -> None:
        """Add triplet."""
        # Note, to enable leveraging existing knowledge graph,
        # the (triplet -- property graph) mapping
        #   makes (n:1) edge_type.prop_name --> triplet.rel
        # thus we have to assume rel to be the first edge_type.prop_name
        # here in upsert_triplet().
        # This applies to the type of entity(tags) with subject and object, too,
        # thus we have to assume subj to be the first entity.tag_name

        # lower case subj, rel, obj
        subj = escape_str(subj)
        rel = escape_str(rel)
        obj = escape_str(obj)
        if self._vid_type == "INT64":
            assert all(
                [subj.isdigit(), obj.isdigit()]
            ), "Subject and object should be digit strings in current graph store."
            subj_field = subj
            obj_field = obj
        else:
            subj_field = f"{QUOTE}{subj}{QUOTE}"
            obj_field = f"{QUOTE}{obj}{QUOTE}"
        edge_field = f"{subj_field}->{obj_field}"

        edge_type = self._edge_types[0]
        rel_prop_name = self._rel_prop_names[0]
        entity_type = self._tags[0]
        rel_hash = hash_string_to_rank(rel)
        dml_query = (
            f"INSERT VERTEX `{entity_type}`(name) "
            f"  VALUES {subj_field}:({QUOTE}{subj}{QUOTE});"
            f"INSERT VERTEX `{entity_type}`(name) "
            f"  VALUES {obj_field}:({QUOTE}{obj}{QUOTE});"
            f"INSERT EDGE `{edge_type}`(`{rel_prop_name}`) "
            f"  VALUES "
            f"{edge_field}"
            f"@{rel_hash}:({QUOTE}{rel}{QUOTE});"
        )
        logger.debug(f"upsert_triplet()\nDML query: {dml_query}")
        result = self.execute(dml_query)
        assert (
            result and result.is_succeeded()
        ), f"Failed to upsert triplet: {subj} {rel} {obj}, query: {dml_query}"

