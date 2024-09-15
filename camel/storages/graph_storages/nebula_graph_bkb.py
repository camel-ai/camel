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
from typing import Any, Dict, List, Optional
#TODO: SORT IMPORTS
from camel.storages.graph_storages import BaseGraphStorage, LabelledNode, ChunkNode, EntityNode, Triplet, Relation
from camel.storages.graph_storages.utils import url_scheme_parse, build_param_map, remove_empty_values
from camel.utils import dependencies_required
from string import Template

from nebula3.common import ttypes
from nebula3.gclient.net.SessionPool import SessionPool
from nebula3.gclient.net.base import BaseExecutor
from nebula3.data.ResultSet import ResultSet

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


class NebulaGraphBkb(BaseGraphStorage):
    """NebulaGraph graph store."""

    @dependencies_required('nebula3')
    def __init__(
            self,
            space: str,
            client: Optional[BaseExecutor] = None,
            username: str = "root",
            password: str = "nebula",
            url: str = "nebula://localhost:9669",
            overwrite: bool = False,
            edge_types=None,
            rel_prop_names=None,
            tags=None,
            tag_prop_names=None,
            include_vid: bool = True,
    ) -> None:
        """Initialize NebulaGraph graph store.

        Args:
            #TODO: UPDATE
        """
        self._space = space
        if client:
            self._client = client
        else:
            session_pool = SessionPool(
                username,
                password,
                self._space,
                [url_scheme_parse(url)],
            )
            session_pool.init()
            self._client = session_pool
        if overwrite:
            self._client.execute(f"CLEAR SPACE {self._space};")
        if tag_prop_names is None:
            tag_prop_names = ["name,"]
        if tags is None:
            tags = ["entity"]
        if rel_prop_names is None:
            rel_prop_names = ["relationship,"]
        if edge_types is None:
            edge_types = ["relationship"]
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
    def _get_vid_type(self):
        """Get vid type."""
        return (
            self._execute(f"DESCRIBE SPACE {self._space_name}")
            .column_values("Vid Type")[0]
            .cast()
        )

    @property
    def get_client(self) -> Any:
        """Return NebulaGraph client object."""
        return self._client

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

    def get(
            self,
            properties: Optional[dict] = None,
            ids: Optional[List[str]] = None,
    ) -> List[LabelledNode]:
        """Get nodes."""
        if not (properties or ids):
            return []
        else:
            return self._get(properties, ids)

    def _get(
            self,
            properties: Optional[dict] = None,
            ids: Optional[List[str]] = None,
    ) -> List[LabelledNode]:
        """Get nodes."""
        cypher_statement = "MATCH (e:Node__) "
        if properties or ids:
            cypher_statement += "WHERE "
        params = {}

        if ids:
            cypher_statement += f"id(e) in $all_id "
            params[f"all_id"] = ids
        if properties:
            for i, prop in enumerate(properties):
                cypher_statement += f"e.Prop__.`{prop}` == $property_{i} AND "
                params[f"property_{i}"] = properties[prop]
            cypher_statement = cypher_statement[:-5]  # Remove trailing AND

        return_statement = """
        RETURN id(e) AS name,
               e.Node__.label AS type,
               properties(e.Props__) AS properties,
               properties(e) AS all_props
        """
        cypher_statement += return_statement
        cypher_statement = cypher_statement.replace("\n", " ")

        response = self.structured_query(cypher_statement, param_map=params)

        nodes = []
        for record in response:
            if "text" in record["all_props"]:
                node = ChunkNode(
                    id_=record["name"],
                    label=record["type"],
                    text=record["all_props"]["text"],
                    properties=remove_empty_values(record["properties"]),
                )
            elif "name" in record["all_props"]:
                node = EntityNode(
                    id_=record["name"],
                    label=record["type"],
                    name=record["all_props"]["name"],
                    properties=remove_empty_values(record["properties"]),
                )
            else:
                node = EntityNode(
                    name=record["name"],
                    type=record["type"],
                    properties=remove_empty_values(record["properties"]),
                )
            nodes.append(node)
        return nodes

    def get_all_nodes(self) -> List[LabelledNode]:
        return self._get()

    def get_triplets(
            self,
            entity_names: Optional[List[str]] = None,
            relation_names: Optional[List[str]] = None,
            properties: Optional[dict] = None,
            ids: Optional[List[str]] = None,
    ) -> List[Triplet]:
        cypher_statement = "MATCH (e:`Entity__`)-[r:`Relation__`]->(t:`Entity__`) "
        if not (entity_names or relation_names or properties or ids):
            return []
        else:
            cypher_statement += "WHERE "
        params = {}

        if entity_names:
            cypher_statement += (
                f"e.Entity__.name in $entities OR t.Entity__.name in $entities"
            )
            params[f"entities"] = entity_names
        if relation_names:
            cypher_statement += f"r.label in $relations "
            params[f"relations"] = relation_names
        if properties:
            pass
        if ids:
            cypher_statement += f"id(e) in $all_id OR id(t) in $all_id"
            params[f"all_id"] = ids
        if properties:
            v0_matching = ""
            v1_matching = ""
            edge_matching = ""
            for i, prop in enumerate(properties):
                v0_matching += f"e.Props__.`{prop}` == $property_{i} AND "
                v1_matching += f"t.Props__.`{prop}` == $property_{i} AND "
                edge_matching += f"r.`{prop}` == $property_{i} AND "
                params[f"property_{i}"] = properties[prop]
            v0_matching = v0_matching[:-5]  # Remove trailing AND
            v1_matching = v1_matching[:-5]  # Remove trailing AND
            edge_matching = edge_matching[:-5]  # Remove trailing AND
            cypher_statement += (
                f"({v0_matching}) OR ({edge_matching}) OR ({v1_matching})"
            )

        return_statement = f"""
        RETURN id(e) AS source_id, e.Node__.label AS source_type,
                properties(e.Props__) AS source_properties,
                r.label AS type,
                properties(r) AS rel_properties,
                id(t) AS target_id, t.Node__.label AS target_type,
                properties(t.Props__) AS target_properties
        """
        cypher_statement += return_statement
        cypher_statement = cypher_statement.replace("\n", " ")

        data = self.structured_query(cypher_statement, param_map=params)

        triples = []
        for record in data:
            source = EntityNode(
                name=record["source_id"],
                label=record["source_type"],
                properties=remove_empty_values(record["source_properties"]),
            )
            target = EntityNode(
                name=record["target_id"],
                label=record["target_type"],
                properties=remove_empty_values(record["target_properties"]),
            )
            rel_properties = remove_empty_values(record["rel_properties"])
            rel_properties.pop("label")
            rel = Relation(
                source_id=record["source_id"],
                target_id=record["target_id"],
                label=record["type"],
                properties=rel_properties,
            )
            triples.append((source, rel, target))
        return triples

    def get_rel_map(
            self,
            graph_nodes: List[LabelledNode],
            depth: int = 2,
            limit: int = 30,
            ignore_rels: Optional[List[str]] = None,
    ) -> List[Triplet]:
        """Get depth-aware rel map."""
        triples = []

        ids = [node.id for node in graph_nodes]
        # Needs some optimization
        response = self.structured_query(
            f"""
            MATCH (e:`Entity__`)
            WHERE id(e) in $ids
            MATCH p=(e)-[r*1..{depth}]-(other)
            WHERE ALL(rel in relationships(p) WHERE rel.`label` <> 'MENTIONS')
            UNWIND relationships(p) AS rel
            WITH distinct rel
            WITH startNode(rel) AS source,
                rel.`label` AS type,
                endNode(rel) AS endNode
            MATCH (v) WHERE id(v)==id(source) WITH v AS source, type, endNode
            MATCH (v) WHERE id(v)==id(endNode) WITH source, type, v AS endNode
            RETURN id(source) AS source_id, source.`Node__`.`label` AS source_type,
                    properties(source.`Props__`) AS source_properties,
                    type,
                    id(endNode) AS target_id, endNode.`Node__`.`label` AS target_type,
                    properties(endNode.`Props__`) AS target_properties
            LIMIT {limit}
            """,
            param_map={"ids": ids},
        )

        ignore_rels = ignore_rels or []
        for record in response:
            if record["type"] in ignore_rels:
                continue

            source = EntityNode(
                name=record["source_id"],
                label=record["source_type"],
                properties=remove_empty_values(record["source_properties"]),
            )
            target = EntityNode(
                name=record["target_id"],
                label=record["target_type"],
                properties=remove_empty_values(record["target_properties"]),
            )
            rel = Relation(
                source_id=record["source_id"],
                target_id=record["target_id"],
                label=record["type"],
            )
            triples.append([source, rel, target])

        return triples

    def _construct_property_query(self, properties: Dict[str, Any]):
        keys = ",".join([f"`{k}`" for k in properties])
        values_k = ""
        values_params: Dict[Any] = {}
        for idx, v in enumerate(properties.values()):
            values_k += f"$kv_{idx},"
            values_params[f"kv_{idx}"] = v
        values_k = values_k[:-1]
        return keys, values_k, values_params

    def structured_query(
            self, query: str, param_map: Optional[Dict[str, Any]] = None
    ) -> Any:
        if not param_map:
            result = self._client.execute(query)
        else:
            result = self._client.execute_parameter(query, build_param_map(param_map))
        if not result.is_succeeded():
            raise Exception(
                "NebulaGraph query failed:",
                result.error_msg(),
                "Statement:",
                query,
                "Params:",
                param_map,
            )
        full_result = [
            {
                key: result.row_values(row_index)[i].cast_primitive()
                for i, key in enumerate(result.keys())
            }
            for row_index in range(result.row_size())
        ]

        return full_result

    def add_graph_elements(self, nodes: List[LabelledNode]) -> None:
        # meta tag Entity__ is used to store the entity name
        # meta tag Chunk__ is used to store the chunk text
        # other labels are used to store the entity properties
        # which must be created before upserting the nodes

        # Lists to hold separated types
        entity_list: List[EntityNode] = []
        chunk_list: List[ChunkNode] = []
        other_list: List[LabelledNode] = []

        # Sort by type
        for item in nodes:
            if isinstance(item, EntityNode):
                entity_list.append(item)
            elif isinstance(item, ChunkNode):
                chunk_list.append(item)
            else:
                other_list.append(item)

        if chunk_list:
            # TODO: need to double check other properties if any(it seems for now only text is there)
            # model chunk as tag and perform upsert
            # i.e. INSERT VERTEX `Chunk__` (`text`) VALUES "foo":("hello world"), "baz":("lorem ipsum");
            insert_query = "INSERT VERTEX `Chunk__` (`text`) VALUES "
            for i, chunk in enumerate(chunk_list):
                insert_query += f'"{chunk.id}":($chunk_{i}),'
            insert_query = insert_query[:-1]  # Remove trailing comma
            self.structured_query(
                insert_query,
                param_map={
                    f"chunk_{i}": chunk.text for i, chunk in enumerate(chunk_list)
                },
            )

        if entity_list:
            # model with tag Entity__ and other tags(label) if applicable
            # need to add properties as well, for extractors like SchemaLLMPathExtractor there is no properties
            # NebulaGraph is Schema-Full, so we need to be strong schema mindset to abstract this.
            # i.e.
            # INSERT VERTEX Entity__ (name) VALUES "foo":("bar"), "baz":("qux");
            # INSERT VERTEX Person (name) VALUES "foo":("bar"), "baz":("qux");

            # The meta tag Entity__ is used to store the entity name
            insert_query = "INSERT VERTEX `Entity__` (`name`) VALUES "
            for i, entity in enumerate(entity_list):
                insert_query += f'"{entity.id}":($entity_{i}),'
            insert_query = insert_query[:-1]  # Remove trailing comma
            self.structured_query(
                insert_query,
                param_map={
                    f"entity_{i}": entity.name for i, entity in enumerate(entity_list)
                },
            )

        # Create tags for each LabelledNode
        # This could be revisited, if we don't have any properties for labels, mapping labels to
        # Properties of tag: Entity__ is also feasible.
        for i, entity in enumerate(nodes):
            keys, values_k, values_params = self._construct_property_query(
                entity.properties
            )
            stmt = f'INSERT VERTEX Props__ ({keys}) VALUES "{entity.id}":({values_k});'
            self.structured_query(
                stmt,
                param_map=values_params,
            )
            stmt = (
                f'INSERT VERTEX Node__ (label) VALUES "{entity.id}":("{entity.label}");'
            )
            self.structured_query(stmt)

    def _execute(self, query: str) -> ResultSet:
        return self._client.execute(query)

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
