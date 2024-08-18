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

from nebula3.common import ttypes
from nebula3.Config import SessionPoolConfig
from nebula3.Exception import IOErrorException
from nebula3.fbthrift.transport.TTransport import TTransportException
from nebula3.gclient.net.SessionPool import SessionPool

BASE_ENTITY_LABEL: str = "entity"
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


def _hash_string_to_rank(string: str) -> int:
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


def _prepare_subjs_param(
        subjs: Optional[List[str]], vid_type: str = "FIXED_STRING(256)"
) -> Dict:
    """Prepare parameters for query."""
    if subjs is None:
        return {}

    subjs_list = []
    subjs_byte = ttypes.Value()

    # filter non-digit string for INT64 vid type
    if vid_type == "INT64":
        subjs = [subj for subj in subjs if subj.isdigit()]
        if len(subjs) == 0:
            logger.warning(
                f"KG is with INT64 vid type, but no digit string is provided."
                f"Return empty subjs, and no query will be executed."
                f"subjs: {subjs}"
            )
            return {}
    for subj in subjs:
        if not isinstance(subj, str):
            raise TypeError(f"Subject should be str, but got {type(subj).__name__}.")
        subj_byte = ttypes.Value()
        if vid_type == "INT64":
            assert subj.isdigit(), (
                "Subject should be a digit string in current "
                "graph store, where vid type is INT64."
            )
            subj_byte.set_iVal(int(subj))
        else:
            subj_byte.set_sVal(subj)
        subjs_list.append(subj_byte)
    subjs_nlist = ttypes.NList()
    subjs_nlist.values = subjs_list
    subjs_byte.set_lVal(subjs_nlist)
    return {"subjs": subjs_byte}


def _escape_str(value: str) -> str:
    """Escape String for NebulaGraph Query."""
    patterns = {
        '"': " ",
    }
    for pattern in patterns:
        if pattern in value:
            value = value.replace(pattern, patterns[pattern])
    if value[0] == " " or value[-1] == " ":
        value = value.strip()

    return value


class NebulaGraph(BaseGraphStorage):
    """NebulaGraph graph store."""

    @dependencies_required('nebula3')
    def __init__(
            self,
            session_pool: Optional[Any] = None,
            space_name: Optional[str] = None,
            edge_types=None,
            rel_prop_names=None,
            tags=None,
            tag_prop_names=None,
            include_vid: bool = True,
            session_pool_kwargs=None,
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
        """

        if session_pool_kwargs is None:
            session_pool_kwargs = {}
        if tag_prop_names is None:
            tag_prop_names = ["name,"]
        if tags is None:
            tags = ["entity"]
        if rel_prop_names is None:
            rel_prop_names = ["relationship,"]
        if edge_types is None:
            edge_types = ["relationship"]
        assert space_name is not None, "space_name should be provided."
        self._space_name = space_name
        self._session_pool_kwargs = session_pool_kwargs

        self._session_pool: Any = session_pool
        if self._session_pool is None:
            self.init_session_pool()

        self._vid_type = self._get_vid_type

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
            "map{{0}}".format(", ".join(
                [
                    f"`{edge_type}`: \"{','.join(rel_prop_names)}\""
                    for edge_type, rel_prop_names in self._edge_prop_map.items()
                ]
            ))
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

        # init the schema
        self.schema: str = ""
        self.structured_schema: Dict[str, Any] = {}
        # Set schema
        try:
            self.refresh_schema()
        except Exception as e:
            raise ValueError(
                f"Could not refresh schema. Please ensure that the NebulaGraph "
                f"is properly configured and accessible. Error: {str(e)}"
            )

    @property
    def init_session_pool(self) -> Any:
        """Return NebulaGraph session pool."""
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

    @property
    def _get_vid_type(self):
        """Get vid type."""
        return (
            self._execute(f"DESCRIBE SPACE {self._space_name}")
            .column_values("Vid Type")[0]
            .cast()
        )

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

    @property
    def get_structured_schema(self) -> Dict[str, Any]:
        """Returns the structured schema of the graph

        Returns:
            Dict[str, Any]: The structured schema of the graph.
        """
        return self.structured_schema

    def get(self, subj: str) -> List[List[str]]:
        """Get triplets.

        Args:
            subj: Subject.

        Returns:
            Triplets.
        """
        rel_map = self.get_flat_rel_map([subj], depth=1)
        rels = list(rel_map.values())
        if len(rels) == 0:
            return []
        return rels[0]

    def get_flat_rel_map(
            self, subjs: Optional[List[str]] = None, depth: int = 2, limit: int = 30
    ) -> Dict[str, List[List[str]]]:
        """Get flat rel map."""
        # The flat means for multi-hop relation path, we could get
        # knowledge like: subj -rel-> obj -rel-> obj <-rel- obj.
        # This type of knowledge is useful for some tasks.
        # +---------------------+---------------------------------------------...-----+
        # | subj                | flattened_rels                              ...     |
        # +---------------------+---------------------------------------------...-----+
        # | "{name:Tony Parker}"| "{name: Tony Parker}-[follow:{degree:95}]-> ...ili}"|
        # | "{name:Tony Parker}"| "{name: Tony Parker}-[follow:{degree:95}]-> ...r}"  |
        # ...
        rel_map: Dict[Any, List[Any]] = {}
        if subjs is None or len(subjs) == 0:
            # unlike simple graph_store, we don't do get_all here
            return rel_map

        # WITH map{`true`: "-[", `false`: "<-["} AS arrow_l,
        #      map{`true`: "]->", `false`: "]-"} AS arrow_r,
        #      map{`follow`: "degree", `serve`: "start_year,end_year"} AS edge_type_map
        # MATCH p=(start)-[e:follow|serve*..2]-()
        #     WHERE id(start) IN ["player100", "player101"]
        #   WITH start, id(start) AS vid, nodes(p) AS nodes, e AS rels,
        #     length(p) AS rel_count, arrow_l, arrow_r, edge_type_map
        #   WITH
        #     REDUCE(s = vid + '{', key IN [key_ in ["name"]
        #       WHERE properties(start)[key_] IS NOT NULL]  | s + key + ': ' +
        #         COALESCE(TOSTRING(properties(start)[key]), 'null') + ', ')
        #         + '}'
        #       AS subj,
        #     [item in [i IN RANGE(0, rel_count - 1) | [nodes[i], nodes[i + 1],
        #         rels[i], typeid(rels[i]) > 0, type(rels[i]) ]] | [
        #      arrow_l[tostring(item[3])] +
        #          item[4] + ':' +
        #          REDUCE(s = '{', key IN SPLIT(edge_type_map[item[4]], ',') |
        #            s + key + ': ' + COALESCE(TOSTRING(properties(item[2])[key]),
        #            'null') + ', ') + '}'
        #           +
        #      arrow_r[tostring(item[3])],
        #      REDUCE(s = id(item[1]) + '{', key IN [key_ in ["name"]
        #           WHERE properties(item[1])[key_] IS NOT NULL]  | s + key + ': ' +
        #           COALESCE(TOSTRING(properties(item[1])[key]), 'null') + ', ') + '}'
        #      ]
        #   ] AS rels
        #   WITH
        #       REPLACE(subj, ', }', '}') AS subj,
        #       REDUCE(acc = collect(NULL), l in rels | acc + l) AS flattened_rels
        #   RETURN
        #     subj,
        #     REPLACE(REDUCE(acc = subj,l in flattened_rels|acc + ' ' + l),
        #       ', }', '}')
        #       AS flattened_rels
        #   LIMIT 30

        # Based on self._include_vid
        # {name: Tim Duncan} or player100{name: Tim Duncan} for entity
        s_prefix = "vid + '{'" if self._include_vid else "'{'"
        s1 = "id(item[1]) + '{'" if self._include_vid else "'{'"

        query = (
            f"WITH map{{`true`: '-[', `false`: '<-['}} AS arrow_l,"
            f"     map{{`true`: ']->', `false`: ']-'}} AS arrow_r,"
            f"     {self._edge_prop_map_cypher_string} AS edge_type_map "
            f"MATCH p=(start)-[e:`{'`|`'.join(self._edge_types)}`*..{depth}]-() "
            f"  WHERE id(start) IN $subjs "
            f"WITH start, id(start) AS vid, nodes(p) AS nodes, e AS rels,"
            f"  length(p) AS rel_count, arrow_l, arrow_r, edge_type_map "
            f"WITH "
            f"  REDUCE(s = {s_prefix}, key IN [key_ in {self._tag_prop_names!s} "
            f"    WHERE properties(start)[key_] IS NOT NULL]  | s + key + ': ' + "
            f"      COALESCE(TOSTRING(properties(start)[key]), 'null') + ', ')"
            f"      + '}}'"
            f"    AS subj,"
            f"  [item in [i IN RANGE(0, rel_count - 1)|[nodes[i], nodes[i + 1],"
            f"      rels[i], typeid(rels[i]) > 0, type(rels[i]) ]] | ["
            f"    arrow_l[tostring(item[3])] +"
            f"      item[4] + ':' +"
            f"      REDUCE(s = '{{', key IN SPLIT(edge_type_map[item[4]], ',') | "
            f"        s + key + ': ' + COALESCE(TOSTRING(properties(item[2])[key]),"
            f"        'null') + ', ') + '}}'"
            f"      +"
            f"    arrow_r[tostring(item[3])],"
            f"    REDUCE(s = {s1}, key IN [key_ in "
            f"        {self._tag_prop_names!s} WHERE properties(item[1])[key_] "
            f"        IS NOT NULL]  | s + key + ': ' + "
            f"        COALESCE(TOSTRING(properties(item[1])[key]), 'null') + ', ')"
            f"        + '}}'"
            f"    ]"
            f"  ] AS rels "
            f"WITH "
            f"  REPLACE(subj, ', }}', '}}') AS subj,"
            f"  REDUCE(acc = collect(NULL), l in rels | acc + l) AS flattened_rels "
            f"RETURN "
            f"  subj,"
            f"  REPLACE(REDUCE(acc = subj, l in flattened_rels | acc + ' ' + l), "
            f"    ', }}', '}}') "
            f"    AS flattened_rels"
            f"  LIMIT {limit}"
        )
        subjs_param = _prepare_subjs_param(subjs, self._vid_type)
        logger.debug(f"get_flat_rel_map()\nsubjs_param: {subjs},\nquery: {query}")
        if subjs_param == {}:
            # This happens when subjs is None after prepare_subjs_param()
            # Probably because vid type is INT64, but no digit string is provided.
            return rel_map
        result = self._execute(query, subjs_param)
        if result is None:
            return rel_map

        # get raw data
        subjs_ = result.column_values("subj") or []
        rels_ = result.column_values("flattened_rels") or []

        for subj, rel in zip(subjs_, rels_):
            subj_ = subj.cast()
            rel_ = rel.cast()
            if subj_ not in rel_map:
                rel_map[subj_] = []
            rel_map[subj_].append(rel_)
        return rel_map

    def get_rel_map(
            self, subjs: Optional[List[str]] = None, depth: int = 2, limit: int = 30
    ) -> Dict[str, List[List[str]]]:
        """Get rel map."""
        # We put rels in a long list for depth>= 1, this is different from
        # But this makes more sense for multi-hop relation path.

        if subjs is not None:
            subjs = [
                _escape_str(subj) for subj in subjs if isinstance(subj, str) and subj
            ]
            if len(subjs) == 0:
                return {}

        return self.get_flat_rel_map(subjs, depth, limit)

    def add_graph_elements(
            self,
            graph_elements: List[GraphElement],
            include_source: bool = False,
            base_entity_label: bool = False,
    ) -> None:
        """Adds nodes and relationships from a list of GraphElement objects
        to the NebulaGraph storage.
        """
        if base_entity_label:
            # Create a tag for base entity if it doesn't exist
            self._create_base_entity_tag()

        for element in graph_elements:
            if not element.source.to_dict().get('element_id'):
                element.source.to_dict()['element_id'] = md5(
                    str(element).encode("utf-8")
                ).hexdigest()

            # Import nodes
            self._import_nodes(element.nodes, include_source, base_entity_label, element.source)

            # Import relationships
            self._import_relationships(element.relationships)

    def _create_base_entity_tag(self):
        """Creates a base entity tag if it doesn't exist."""
        query = f"CREATE TAG IF NOT EXISTS {BASE_ENTITY_LABEL} (id string)"
        self.query(query)

    def _import_nodes(self, nodes, include_source: bool, base_entity_label: bool, source):
        for node in nodes:
            properties = ", ".join([f"{k}: '{v}'" for k, v in node.__dict__.items() if k != 'id'])
            query = f"INSERT VERTEX `{node.type}` ({properties}) VALUES '{node.id}':({properties})"
            if base_entity_label:
                query += f"; INSERT VERTEX {BASE_ENTITY_LABEL} (id) VALUES '{node.id}':({node.id})"
            if include_source:
                source_id = source.to_dict().get('element_id')
                query += f"; INSERT EDGE MENTIONS () VALUES '{source_id}' -> '{node.id}':({{}});"
            self.query(query)

    def _import_relationships(self, relationships):
        for rel in relationships:
            properties = ", ".join([f"{k}: '{v}'" for k, v in rel.properties.items()])
            query = (f"INSERT EDGE `{rel.type}` ({properties}) VALUES "
                     f"'{rel.subj.id}' -> '{rel.obj.id}':({properties})")
            self.query(query)

    def _execute(self, query: str, param_map=None) -> Any:
        """Execute query.

        Args:
            query: Query.
            param_map: Parameter map.

        Returns:
            Query result.
        """
        if param_map is None:
            param_map = {}
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

    def query(self, query: str, param_map=None) -> Any:
        if param_map is None:
            param_map = {}
        result = self._execute(query, param_map)
        columns = result.keys()
        d: Dict[str, list] = {}
        for col_num in range(result.col_size()):
            col_name = columns[col_num]
            col_list = result.column_values(col_name)
            d[col_name] = [x.cast() for x in col_list]
        return d

    def refresh_schema(self) -> None:
        """
        Refreshes the NebulaGraph Store Schema.
        """
        tags_schema, edge_types_schema, relationships = [], [], []
        for tag in self._execute("SHOW TAGS").column_values("Name"):
            tag_name = tag.cast()
            tag_schema = {"tag": tag_name, "properties": []}
            r = self._execute(f"DESCRIBE TAG `{tag_name}`")
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
        for edge_type in self._execute("SHOW EDGES").column_values("Name"):
            edge_type_name = edge_type.cast()
            edge_schema = {"edge": edge_type_name, "properties": []}
            r = self._execute(f"DESCRIBE EDGE `{edge_type_name}`")
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
            sample_edge = self._execute(
                rel_query_sample_edge.substitute(edge_type=edge_type_name)
            ).column_values("sample_edge")
            if len(sample_edge) == 0:
                continue
            src_id, dst_id = sample_edge[0].cast()
            r = self._execute(
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
        # Update the structured schema
        self.structured_schema = {
            "node_props": {tag["tag"]: tag["properties"] for tag in tags_schema},
            "edge_props": {edge["edge"]: edge["properties"] for edge in edge_types_schema},
            "relationships": relationships,
        }

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
        subj = _escape_str(subj)
        rel = _escape_str(rel)
        obj = _escape_str(obj)
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
        rel_hash = _hash_string_to_rank(rel)
        dml_query = f"""
           INSERT VERTEX `{entity_type}`(name) VALUES {subj_field}:("{subj}");
           INSERT VERTEX `{entity_type}`(name) VALUES {obj_field}:("{obj}");
           INSERT EDGE `{edge_type}`(`{rel_prop_name}`) VALUES {edge_field}@{rel_hash}:("{rel}");
           """
        logger.debug(f"upsert_triplet()\nDML query: {dml_query}")
        result = self._execute(dml_query)
        assert (
                result and result.is_succeeded()
        ), f"Failed to upsert triplet: {subj} {rel} {obj}, query: {dml_query}"

    def delete_triplet(self, subj: str, rel: str, obj: str) -> None:
        """Delete triplet.
        1. Similar to upsert_triplet(),
           we have to assume rel to be the first edge_type.prop_name.
        2. After edge being deleted, we need to check if the subj or
           obj are isolated vertices,
           if so, delete them, too.
        """
        # lower case subj, rel, obj
        subj = _escape_str(subj)
        rel = _escape_str(rel)
        obj = _escape_str(obj)

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

        # DELETE EDGE serve "player100" -> "team204"@7696463696635583936;
        edge_type = self._edge_types[0]
        # rel_prop_name = self._rel_prop_names[0]
        rel_hash = _hash_string_to_rank(rel)
        dml_query = f"DELETE EDGE `{edge_type}`" f"  {edge_field}@{rel_hash};"
        logger.debug(f"delete()\nDML query: {dml_query}")
        result = self._execute(dml_query)
        assert (
                result and result.is_succeeded()
        ), f"Failed to delete triplet: {subj} {rel} {obj}, query: {dml_query}"
        # Get isolated vertices to be deleted
        # MATCH (s) WHERE id(s) IN ["player700"] AND NOT (s)-[]-()
        # RETURN id(s) AS isolated
        query = (
            f"MATCH (s) "
            f"  WHERE id(s) IN [{subj_field}, {obj_field}] "
            f"  AND NOT (s)-[]-() "
            f"RETURN id(s) AS isolated"
        )
        result = self._execute(query)
        isolated = result.column_values("isolated")
        if not isolated:
            return
        # DELETE VERTEX "player700" or DELETE VERTEX 700
        quote_field = QUOTE if self._vid_type != "INT64" else ""
        vertex_ids = ",".join(
            [f"{quote_field}{v.cast()}{quote_field}" for v in isolated]
        )
        dml_query = f"DELETE VERTEX {vertex_ids};"

        result = self._execute(dml_query)
        assert (
                result and result.is_succeeded()
        ), f"Failed to delete isolated vertices: {isolated}, query: {dml_query}"
