"""Neo4j graph utility functions for concept and relationship storage."""

from __future__ import annotations

from typing import Iterable, Optional

from neo4j import GraphDatabase, Driver, Session

from datetime import datetime

from .concept_models import Concept, ConceptMention
from .relationship_models import ExtractedRelationships, Relationship


def _concept_to_dict(concept: Concept) -> dict:
    return {
        "id": str(concept.id),
        "name": concept.name,
        "definition": concept.definition,
        "type": concept.type.value,
        "importance": float(concept.importance),
        "confidence": float(concept.confidence),
        "aliases": concept.aliases,
        "videoId": concept.video_id,
        "groupId": int(concept.group_id),
        "firstMentionTime": float(concept.first_mention_time),
        "lastMentionTime": float(concept.last_mention_time),
        "mentionCount": int(concept.mention_count),
        "extractedAt": concept.extracted_at.isoformat(),
    }


def _mention_to_dict(mention: ConceptMention) -> dict:
    return {
        "id": str(mention.id),
        "surface": mention.surface,
        "timestamp": float(mention.timestamp),
        "salience": float(mention.salience),
        "videoId": mention.video_id,
        "groupId": int(mention.group_id),
        "conceptId": str(mention.concept_id),
        "offsetStart": mention.offset_start,
        "offsetEnd": mention.offset_end,
    }


def _relationship_to_dict(relationship: Relationship) -> dict:
    return {
        "id": str(relationship.id),
        "type": relationship.type.value,
        "relType": relationship.type.value.upper(),
        "confidence": float(relationship.confidence),
        "evidence": relationship.evidence,
        "detectionMethod": relationship.detection_method.value,
        "sourceConceptId": str(relationship.source_concept_id),
        "targetConceptId": str(relationship.target_concept_id),
        "sourceVideoId": relationship.source_video_id,
        "sourceGroupId": int(relationship.source_group_id),
        "targetVideoId": relationship.target_video_id,
        "targetGroupId": int(relationship.target_group_id),
        "temporalDistance": relationship.temporal_distance,
        "extractedAt": relationship.extracted_at.isoformat(),
    }


class Neo4jGraph:
    """Lightweight Neo4j helper used by concept and relationship uploaders."""

    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        database: Optional[str] = None,
    ) -> None:
        self._driver: Driver = GraphDatabase.driver(uri, auth=(user, password))
        self._database = database
        self._ensure_constraints()

    def close(self) -> None:
        self._driver.close()

    # ------------------------------------------------------------------
    # Constraint & index setup
    # ------------------------------------------------------------------
    def _ensure_constraints(self) -> None:
        statements = [
            "CREATE CONSTRAINT concept_id IF NOT EXISTS FOR (c:Concept) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT mention_id IF NOT EXISTS FOR (m:ConceptMention) REQUIRE m.id IS UNIQUE",
            "CREATE CONSTRAINT relationship_id IF NOT EXISTS FOR ()-[r:GRAPH_RELATION]-() REQUIRE r.id IS UNIQUE",
        ]
        with self._driver.session(database=self._database) as session:
            for statement in statements:
                session.execute_write(lambda tx, stmt: tx.run(stmt), statement)

    # ------------------------------------------------------------------
    # Concept operations
    # ------------------------------------------------------------------
    def upsert_concepts(self, concepts: Iterable[Concept]) -> tuple[int, int]:
        payload = [_concept_to_dict(c) for c in concepts]
        if not payload:
            return (0, 0)
        query = """
        UNWIND $concepts AS concept
        MERGE (c:Concept {id: concept.id})
        SET c.name = concept.name,
            c.definition = concept.definition,
            c.type = concept.type,
            c.importance = concept.importance,
            c.confidence = concept.confidence,
            c.aliases = concept.aliases,
            c.videoId = concept.videoId,
            c.groupId = concept.groupId,
            c.firstMentionTime = concept.firstMentionTime,
            c.lastMentionTime = concept.lastMentionTime,
            c.mentionCount = concept.mentionCount,
            c.extractedAt = concept.extractedAt
        RETURN count(c) AS updated
        """
        with self._driver.session(database=self._database) as session:
            result = session.execute_write(
                lambda tx: tx.run(query, concepts=payload).single()["updated"]
            )
        return (int(result), 0)

    def upsert_mentions(self, mentions: Iterable[ConceptMention]) -> tuple[int, int]:
        payload = [_mention_to_dict(m) for m in mentions]
        if not payload:
            return (0, 0)
        query = """
        UNWIND $mentions AS mention
        MERGE (m:ConceptMention {id: mention.id})
        SET m.surface = mention.surface,
            m.timestamp = mention.timestamp,
            m.salience = mention.salience,
            m.videoId = mention.videoId,
            m.groupId = mention.groupId,
            m.offsetStart = mention.offsetStart,
            m.offsetEnd = mention.offsetEnd
        WITH mention, m
        MATCH (c:Concept {id: mention.conceptId})
        MERGE (m)-[:MENTIONS]->(c)
        RETURN count(m) AS updated
        """
        with self._driver.session(database=self._database) as session:
            result = session.execute_write(
                lambda tx: tx.run(query, mentions=payload).single()["updated"]
            )
        return (int(result), 0)

    def delete_concepts_for_video(self, video_id: str) -> int:
        query = """
        MATCH (c:Concept {videoId: $video_id})
        OPTIONAL MATCH (c)<-[:MENTIONS]-(m:ConceptMention)
        DETACH DELETE c, m
        RETURN count(c) AS deleted
        """
        with self._driver.session(database=self._database) as session:
            result = session.execute_write(
                lambda tx: tx.run(query, video_id=video_id).single()["deleted"]
            )
        return int(result)

    def concept_exists(self, concept_id: str) -> bool:
        query = """MATCH (c:Concept {id: $concept_id}) RETURN c LIMIT 1"""
        with self._driver.session(database=self._database) as session:
            result = session.execute_read(
                lambda tx: tx.run(query, concept_id=concept_id).single()
            )
        return result is not None

    def get_concepts_for_video(self, video_id: str) -> list[dict]:
        query = """
        MATCH (c:Concept {videoId: $video_id})
        RETURN c ORDER BY c.importance DESC
        """
        with self._driver.session(database=self._database) as session:
            result = session.execute_read(
                lambda tx: [record["c"] for record in tx.run(query, video_id=video_id)]
            )
        return [dict(record) for record in result]

    def get_concepts_for_group(self, video_id: str, group_id: int) -> list[dict]:
        query = """
        MATCH (c:Concept {videoId: $video_id, groupId: $group_id})
        RETURN c ORDER BY c.importance DESC
        """
        with self._driver.session(database=self._database) as session:
            result = session.execute_read(
                lambda tx: [
                    record["c"]
                    for record in tx.run(query, video_id=video_id, group_id=group_id)
                ]
            )
        return [dict(record) for record in result]

    def search_concepts(
        self,
        query_text: str,
        limit: int = 10,
        min_confidence: float = 0.0,
    ) -> list[dict]:
        cypher = """
        MATCH (c:Concept)
        WHERE (toLower(c.name) CONTAINS toLower($query)
               OR toLower(c.definition) CONTAINS toLower($query))
          AND c.confidence >= $min_confidence
        RETURN c
        ORDER BY c.importance DESC, c.confidence DESC
        LIMIT $limit
        """
        with self._driver.session(database=self._database) as session:
            result = session.execute_read(
                lambda tx: [
                    record["c"]
                    for record in tx.run(
                        cypher,
                        query=query_text,
                        limit=limit,
                        min_confidence=min_confidence,
                    )
                ]
            )
        records = [dict(record) for record in result]
        for rec in records:
            rec["similarity"] = None
        return records

    def get_statistics(self) -> dict:
        cypher = """MATCH (c:Concept) RETURN count(c) AS concepts"""
        with self._driver.session(database=self._database) as session:
            total = session.execute_read(lambda tx: tx.run(cypher).single()["concepts"])
        return {
            "total_concepts": int(total),
            "collections_available": ["Concept", "ConceptMention", "Relationship"],
        }

    # ------------------------------------------------------------------
    # Relationship operations
    # ------------------------------------------------------------------
    def upsert_relationships(
        self,
        relationships: ExtractedRelationships,
        batch_size: int = 100,
    ) -> dict[str, int]:
        rel_dicts = [_relationship_to_dict(rel) for rel in relationships.relationships]
        uploaded = 0
        failed = 0
        skipped = 0
        if not rel_dicts:
            return {"uploaded": 0, "failed": 0, "skipped": 0}

        query = """
        UNWIND $batch AS rel
        MATCH (source:Concept {id: rel.sourceConceptId})
        MATCH (target:Concept {id: rel.targetConceptId})
        MERGE (source)-[r:GRAPH_RELATION {id: rel.id}]->(target)
        ON CREATE SET r.type = rel.relType
        SET r.confidence = rel.confidence,
            r.evidence = rel.evidence,
            r.detectionMethod = rel.detectionMethod,
            r.sourceVideoId = rel.sourceVideoId,
            r.sourceGroupId = rel.sourceGroupId,
            r.targetVideoId = rel.targetVideoId,
            r.targetGroupId = rel.targetGroupId,
            r.temporalDistance = rel.temporalDistance,
            r.extractedAt = rel.extractedAt
        RETURN count(r) AS added
        """
        with self._driver.session(database=self._database) as session:
            for i in range(0, len(rel_dicts), batch_size):
                batch = rel_dicts[i : i + batch_size]
                result = session.execute_write(
                    lambda tx, params: tx.run(query, batch=params).single()["added"],
                    batch,
                )
                uploaded += int(result)
        return {"uploaded": uploaded, "failed": failed, "skipped": skipped}

    def delete_relationships_for_video(self, video_id: str) -> int:
        cypher = """
        MATCH ()-[r:GRAPH_RELATION]-()
        WHERE r.sourceVideoId = $video_id OR r.targetVideoId = $video_id
        DELETE r
        RETURN count(r) AS deleted
        """
        with self._driver.session(database=self._database) as session:
            result = session.execute_write(
                lambda tx: tx.run(cypher, video_id=video_id).single()["deleted"]
            )
        return int(result)

    def count_relationships(self, video_id: Optional[str] = None) -> int:
        if video_id:
            cypher = """
            MATCH ()-[r:GRAPH_RELATION]-()
            WHERE r.sourceVideoId = $video_id OR r.targetVideoId = $video_id
            RETURN count(r) AS total
            """
            params = {"video_id": video_id}
        else:
            cypher = """MATCH ()-[r:GRAPH_RELATION]-() RETURN count(r) AS total"""
            params = {}
        with self._driver.session(database=self._database) as session:
            result = session.execute_read(
                lambda tx: tx.run(cypher, **params).single()["total"]
            )
        return int(result)

    def fetch_relationships_for_concept(
        self, concept_id: str, limit: int = 100
    ) -> list[dict]:
        cypher = """
        MATCH (c:Concept {id: $concept_id})-[r:GRAPH_RELATION]-(other:Concept)
        RETURN r, other
        LIMIT $limit
        """
        with self._driver.session(database=self._database) as session:
            records = session.execute_read(
                lambda tx: [
                    {
                        "relationship": dict(record["r"]),
                        "other": dict(record["other"]),
                    }
                    for record in tx.run(cypher, concept_id=concept_id, limit=limit)
                ]
            )
        return records

    # ------------------------------------------------------------------
    # Concept retrieval for extractor
    # ------------------------------------------------------------------
    def get_extracted_concepts(self, video_id: str) -> list[Concept]:
        cypher = """
        MATCH (c:Concept {videoId: $video_id})
        RETURN c ORDER BY c.groupId, c.importance DESC
        """
        with self._driver.session(database=self._database) as session:
            records = session.execute_read(
                lambda tx: [
                    dict(record["c"]) for record in tx.run(cypher, video_id=video_id)
                ]
            )
        concepts: list[Concept] = []
        for data in records:
            extracted_at = data.get("extractedAt")
            if isinstance(extracted_at, datetime):
                extracted_at_value = extracted_at
            elif extracted_at:
                try:
                    extracted_at_value = datetime.fromisoformat(
                        str(extracted_at).rstrip("Z")
                    )
                except ValueError:
                    extracted_at_value = datetime.utcnow()
            else:
                extracted_at_value = datetime.utcnow()

            concept = Concept(
                name=data["name"],
                definition=data["definition"],
                type=data["type"],
                importance=data["importance"],
                confidence=data["confidence"],
                video_id=data["videoId"],
                group_id=data["groupId"],
                first_mention_time=data["firstMentionTime"],
                last_mention_time=data["lastMentionTime"],
                mention_count=data["mentionCount"],
                aliases=data.get("aliases", []) or [],
                extracted_at=extracted_at_value,
                id=data.get("id"),
            )
            concepts.append(concept)
        return concepts
