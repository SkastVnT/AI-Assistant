"""Graph storage abstraction — protocol + PostgreSQL + Neo4j implementations.

The GraphStore protocol defines the interface for persisting and querying
the knowledge graph. Two implementations are provided:

- PostgresGraphStore: uses the graph_entities / graph_relationships /
  graph_communities tables with pgvector for entity embedding search.
  Zero additional infrastructure — works with the existing PostgreSQL.

- Neo4jGraphStore: uses Neo4j graph database for native graph traversals.
  Higher performance for multi-hop queries at scale.
"""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable
from uuid import UUID

from libs.graph_rag.types import (
    Community,
    Entity,
    GraphNeighbourhood,
    Relationship,
)

logger = logging.getLogger("rag.graph_rag.store")


# ═══════════════════════════════════════════════════════════════════════
# Protocol
# ═══════════════════════════════════════════════════════════════════════


@runtime_checkable
class GraphStore(Protocol):
    """Abstract graph storage interface.

    All methods are async. Implementations must handle tenant isolation.
    """

    # ── Write operations ───────────────────────────────────────────

    async def upsert_entity(
        self, tenant_id: UUID, entity: Entity,
    ) -> Entity:
        """Insert or update an entity (merge by name + type)."""
        ...

    async def upsert_relationship(
        self, tenant_id: UUID, relationship: Relationship,
    ) -> Relationship:
        """Insert or update a relationship (merge by source + target + type)."""
        ...

    async def upsert_community(
        self, tenant_id: UUID, community: Community,
    ) -> Community:
        """Insert or update a community."""
        ...

    async def assign_entity_community(
        self, entity_id: UUID, community_id: UUID,
    ) -> None:
        """Assign an entity to a community."""
        ...

    # ── Read operations ────────────────────────────────────────────

    async def get_entities_by_name(
        self, tenant_id: UUID, names: list[str],
    ) -> list[Entity]:
        """Fetch entities by exact name match."""
        ...

    async def search_entities_by_embedding(
        self,
        tenant_id: UUID,
        query_embedding: list[float],
        *,
        top_k: int = 10,
        score_threshold: float = 0.3,
    ) -> list[tuple[Entity, float]]:
        """Semantic search over entity embeddings. Returns (entity, score)."""
        ...

    async def get_entity_neighbourhood(
        self,
        tenant_id: UUID,
        entity_ids: list[UUID],
        *,
        hops: int = 2,
        max_entities: int = 20,
    ) -> GraphNeighbourhood:
        """Get entities and relationships N hops from seed entities."""
        ...

    async def get_all_entities(
        self, tenant_id: UUID,
    ) -> list[Entity]:
        """Get all entities for a tenant (for community detection)."""
        ...

    async def get_all_relationships(
        self, tenant_id: UUID,
    ) -> list[Relationship]:
        """Get all relationships for a tenant (for community detection)."""
        ...

    async def search_communities_by_embedding(
        self,
        tenant_id: UUID,
        query_embedding: list[float],
        *,
        top_k: int = 10,
    ) -> list[tuple[Community, float]]:
        """Semantic search over community summary embeddings."""
        ...

    # ── Delete operations ──────────────────────────────────────────

    async def delete_entities_for_document(
        self, tenant_id: UUID, document_id: UUID,
    ) -> int:
        """Remove all entities sourced from a document. Returns count."""
        ...


# ═══════════════════════════════════════════════════════════════════════
# PostgreSQL implementation
# ═══════════════════════════════════════════════════════════════════════


class PostgresGraphStore:
    """GraphStore backed by PostgreSQL + pgvector.

    Uses the graph_entities, graph_relationships, graph_communities tables.
    Entity embeddings and community summary embeddings use pgvector HNSW.
    Multi-hop traversal uses recursive CTEs.
    """

    def __init__(self, session_factory) -> None:
        """Accept an async session factory (e.g. async_sessionmaker)."""
        self._session_factory = session_factory

    async def upsert_entity(
        self, tenant_id: UUID, entity: Entity,
    ) -> Entity:
        from libs.core.models import GraphEntity

        async with self._session_factory() as db:
            # Check for existing
            from sqlalchemy import select

            stmt = select(GraphEntity).where(
                GraphEntity.tenant_id == tenant_id,
                GraphEntity.name == entity.name,
                GraphEntity.entity_type == entity.entity_type,
            )
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                existing.description = entity.description or existing.description
                if entity.embedding is not None:
                    existing.embedding = entity.embedding
                # Merge source_chunk_ids (append new, dedup)
                current_ids = existing.source_chunk_ids or []
                new_ids = entity.source_chunk_ids or []
                seen = {str(c.get("chunk_id", "")) for c in current_ids}
                for cid in new_ids:
                    if str(cid.get("chunk_id", "")) not in seen:
                        current_ids.append(cid)
                existing.source_chunk_ids = current_ids
                existing.metadata_ = {**existing.metadata_, **entity.metadata}
                await db.commit()
                entity.id = existing.id
                return entity

            db_entity = GraphEntity(
                tenant_id=tenant_id,
                name=entity.name,
                entity_type=entity.entity_type,
                description=entity.description,
                embedding=entity.embedding,
                source_chunk_ids=entity.source_chunk_ids,
                metadata_=entity.metadata,
            )
            db.add(db_entity)
            await db.commit()
            entity.id = db_entity.id
            return entity

    async def upsert_relationship(
        self, tenant_id: UUID, relationship: Relationship,
    ) -> Relationship:
        from libs.core.models import GraphRelationship

        async with self._session_factory() as db:
            from sqlalchemy import select

            # Resolve entity IDs by name
            from libs.core.models import GraphEntity

            src = await db.execute(
                select(GraphEntity.id).where(
                    GraphEntity.tenant_id == tenant_id,
                    GraphEntity.name == relationship.source_entity,
                )
            )
            src_id = src.scalar_one_or_none()
            tgt = await db.execute(
                select(GraphEntity.id).where(
                    GraphEntity.tenant_id == tenant_id,
                    GraphEntity.name == relationship.target_entity,
                )
            )
            tgt_id = tgt.scalar_one_or_none()

            if not src_id or not tgt_id:
                logger.warning(
                    "skip_relationship: source=%s or target=%s not found",
                    relationship.source_entity,
                    relationship.target_entity,
                )
                return relationship

            # Check existing
            stmt = select(GraphRelationship).where(
                GraphRelationship.tenant_id == tenant_id,
                GraphRelationship.source_entity_id == src_id,
                GraphRelationship.target_entity_id == tgt_id,
                GraphRelationship.relationship_type == relationship.relationship_type,
            )
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                existing.description = (
                    relationship.description or existing.description
                )
                existing.weight = max(existing.weight, relationship.weight)
                current_ids = existing.source_chunk_ids or []
                new_ids = relationship.source_chunk_ids or []
                seen = {str(c.get("chunk_id", "")) for c in current_ids}
                for cid in new_ids:
                    if str(cid.get("chunk_id", "")) not in seen:
                        current_ids.append(cid)
                existing.source_chunk_ids = current_ids
                await db.commit()
                relationship.id = existing.id
                relationship.source_entity_id = src_id
                relationship.target_entity_id = tgt_id
                return relationship

            db_rel = GraphRelationship(
                tenant_id=tenant_id,
                source_entity_id=src_id,
                target_entity_id=tgt_id,
                relationship_type=relationship.relationship_type,
                description=relationship.description,
                weight=relationship.weight,
                source_chunk_ids=relationship.source_chunk_ids,
                metadata_=relationship.metadata,
            )
            db.add(db_rel)
            await db.commit()
            relationship.id = db_rel.id
            relationship.source_entity_id = src_id
            relationship.target_entity_id = tgt_id
            return relationship

    async def upsert_community(
        self, tenant_id: UUID, community: Community,
    ) -> Community:
        from libs.core.models import GraphCommunity

        async with self._session_factory() as db:
            db_community = GraphCommunity(
                tenant_id=tenant_id,
                name=community.name,
                level=community.level,
                summary=community.summary,
                summary_embedding=community.summary_embedding,
                entity_count=len(community.entity_ids),
                relationship_count=community.relationship_count,
                metadata_=community.metadata,
            )
            if community.id:
                db_community.id = community.id
            db.add(db_community)
            await db.commit()
            community.id = db_community.id
            return community

    async def assign_entity_community(
        self, entity_id: UUID, community_id: UUID,
    ) -> None:
        from libs.core.models import GraphEntity

        async with self._session_factory() as db:
            entity = await db.get(GraphEntity, entity_id)
            if entity:
                entity.community_id = community_id
                await db.commit()

    async def get_entities_by_name(
        self, tenant_id: UUID, names: list[str],
    ) -> list[Entity]:
        from libs.core.models import GraphEntity

        async with self._session_factory() as db:
            from sqlalchemy import select

            stmt = select(GraphEntity).where(
                GraphEntity.tenant_id == tenant_id,
                GraphEntity.name.in_(names),
            )
            result = await db.execute(stmt)
            rows = result.scalars().all()
            return [
                Entity(
                    id=r.id,
                    name=r.name,
                    entity_type=r.entity_type,
                    description=r.description,
                    source_chunk_ids=r.source_chunk_ids or [],
                    community_id=r.community_id,
                    metadata=r.metadata_ or {},
                )
                for r in rows
            ]

    async def search_entities_by_embedding(
        self,
        tenant_id: UUID,
        query_embedding: list[float],
        *,
        top_k: int = 10,
        score_threshold: float = 0.3,
    ) -> list[tuple[Entity, float]]:
        from libs.core.models import GraphEntity

        async with self._session_factory() as db:
            from sqlalchemy import select

            # pgvector cosine distance: 1 - distance = similarity
            distance = GraphEntity.embedding.cosine_distance(query_embedding)
            stmt = (
                select(GraphEntity, distance.label("distance"))
                .where(
                    GraphEntity.tenant_id == tenant_id,
                    GraphEntity.embedding.isnot(None),
                )
                .order_by(distance)
                .limit(top_k)
            )
            result = await db.execute(stmt)
            rows = result.all()

            entities: list[tuple[Entity, float]] = []
            for row_entity, dist in rows:
                score = 1.0 - dist
                if score < score_threshold:
                    continue
                entity = Entity(
                    id=row_entity.id,
                    name=row_entity.name,
                    entity_type=row_entity.entity_type,
                    description=row_entity.description,
                    source_chunk_ids=row_entity.source_chunk_ids or [],
                    community_id=row_entity.community_id,
                    metadata=row_entity.metadata_ or {},
                )
                entities.append((entity, score))
            return entities

    async def get_entity_neighbourhood(
        self,
        tenant_id: UUID,
        entity_ids: list[UUID],
        *,
        hops: int = 2,
        max_entities: int = 20,
    ) -> GraphNeighbourhood:
        from libs.core.models import GraphEntity, GraphRelationship

        async with self._session_factory() as db:
            from sqlalchemy import or_, select

            # Gather seed entities
            seed_stmt = select(GraphEntity).where(
                GraphEntity.id.in_(entity_ids),
            )
            seed_result = await db.execute(seed_stmt)
            seed_rows = seed_result.scalars().all()
            seed_entities = [
                Entity(
                    id=r.id, name=r.name, entity_type=r.entity_type,
                    description=r.description,
                    source_chunk_ids=r.source_chunk_ids or [],
                    community_id=r.community_id,
                )
                for r in seed_rows
            ]

            # BFS traversal up to N hops
            visited_ids: set[UUID] = set(entity_ids)
            frontier_ids = set(entity_ids)
            all_relationships: list[Relationship] = []
            neighbour_entities: list[Entity] = []

            for _hop in range(hops):
                if not frontier_ids or len(visited_ids) >= max_entities:
                    break
                rel_stmt = select(GraphRelationship).where(
                    GraphRelationship.tenant_id == tenant_id,
                    or_(
                        GraphRelationship.source_entity_id.in_(frontier_ids),
                        GraphRelationship.target_entity_id.in_(frontier_ids),
                    ),
                )
                rel_result = await db.execute(rel_stmt)
                rel_rows = rel_result.scalars().all()

                next_frontier: set[UUID] = set()
                for r in rel_rows:
                    all_relationships.append(Relationship(
                        id=r.id,
                        source_entity=r.source_entity_id,
                        target_entity=r.target_entity_id,
                        relationship_type=r.relationship_type,
                        description=r.description,
                        weight=r.weight,
                        source_chunk_ids=r.source_chunk_ids or [],
                        source_entity_id=r.source_entity_id,
                        target_entity_id=r.target_entity_id,
                    ))
                    for eid in (r.source_entity_id, r.target_entity_id):
                        if eid not in visited_ids:
                            next_frontier.add(eid)
                            visited_ids.add(eid)

                if next_frontier:
                    trimmed = list(next_frontier)[: max_entities - len(visited_ids)]
                    ent_stmt = select(GraphEntity).where(
                        GraphEntity.id.in_(trimmed),
                    )
                    ent_result = await db.execute(ent_stmt)
                    for r in ent_result.scalars().all():
                        neighbour_entities.append(Entity(
                            id=r.id, name=r.name,
                            entity_type=r.entity_type,
                            description=r.description,
                            source_chunk_ids=r.source_chunk_ids or [],
                            community_id=r.community_id,
                        ))
                frontier_ids = next_frontier

            # Resolve entity names in relationships
            all_ids = visited_ids
            name_stmt = select(
                GraphEntity.id, GraphEntity.name,
            ).where(GraphEntity.id.in_(all_ids))
            name_result = await db.execute(name_stmt)
            id_to_name = {row.id: row.name for row in name_result.all()}

            for r in all_relationships:
                r.source_entity = id_to_name.get(r.source_entity_id, str(r.source_entity_id))
                r.target_entity = id_to_name.get(r.target_entity_id, str(r.target_entity_id))

            # Collect source chunks
            chunk_refs: list[dict] = []
            for e in seed_entities + neighbour_entities:
                chunk_refs.extend(e.source_chunk_ids)

            return GraphNeighbourhood(
                seed_entities=seed_entities,
                neighbour_entities=neighbour_entities,
                relationships=all_relationships,
                source_chunks=chunk_refs,
            )

    async def get_all_entities(self, tenant_id: UUID) -> list[Entity]:
        from libs.core.models import GraphEntity

        async with self._session_factory() as db:
            from sqlalchemy import select

            stmt = select(GraphEntity).where(
                GraphEntity.tenant_id == tenant_id,
            )
            result = await db.execute(stmt)
            return [
                Entity(
                    id=r.id, name=r.name, entity_type=r.entity_type,
                    description=r.description,
                    source_chunk_ids=r.source_chunk_ids or [],
                    community_id=r.community_id,
                    metadata=r.metadata_ or {},
                )
                for r in result.scalars().all()
            ]

    async def get_all_relationships(self, tenant_id: UUID) -> list[Relationship]:
        from libs.core.models import GraphRelationship

        async with self._session_factory() as db:
            from sqlalchemy import select

            stmt = select(GraphRelationship).where(
                GraphRelationship.tenant_id == tenant_id,
            )
            result = await db.execute(stmt)
            return [
                Relationship(
                    id=r.id,
                    source_entity=str(r.source_entity_id),
                    target_entity=str(r.target_entity_id),
                    relationship_type=r.relationship_type,
                    description=r.description,
                    weight=r.weight,
                    source_chunk_ids=r.source_chunk_ids or [],
                    source_entity_id=r.source_entity_id,
                    target_entity_id=r.target_entity_id,
                )
                for r in result.scalars().all()
            ]

    async def search_communities_by_embedding(
        self,
        tenant_id: UUID,
        query_embedding: list[float],
        *,
        top_k: int = 10,
    ) -> list[tuple[Community, float]]:
        from libs.core.models import GraphCommunity

        async with self._session_factory() as db:
            from sqlalchemy import select

            distance = GraphCommunity.summary_embedding.cosine_distance(
                query_embedding,
            )
            stmt = (
                select(GraphCommunity, distance.label("distance"))
                .where(
                    GraphCommunity.tenant_id == tenant_id,
                    GraphCommunity.summary_embedding.isnot(None),
                )
                .order_by(distance)
                .limit(top_k)
            )
            result = await db.execute(stmt)

            communities: list[tuple[Community, float]] = []
            for row_comm, dist in result.all():
                score = 1.0 - dist
                community = Community(
                    id=row_comm.id,
                    name=row_comm.name,
                    level=row_comm.level,
                    summary=row_comm.summary,
                    entity_ids=[],
                    relationship_count=row_comm.relationship_count,
                    metadata=row_comm.metadata_ or {},
                )
                communities.append((community, score))
            return communities

    async def delete_entities_for_document(
        self, tenant_id: UUID, document_id: UUID,
    ) -> int:
        from libs.core.models import GraphEntity

        async with self._session_factory() as db:
            from sqlalchemy import select

            doc_id_str = str(document_id)
            stmt = select(GraphEntity).where(
                GraphEntity.tenant_id == tenant_id,
            )
            result = await db.execute(stmt)
            deleted = 0
            for entity in result.scalars().all():
                refs = entity.source_chunk_ids or []
                if any(str(r.get("document_id", "")) == doc_id_str for r in refs):
                    await db.delete(entity)
                    deleted += 1
            await db.commit()
            return deleted


# ═══════════════════════════════════════════════════════════════════════
# Neo4j stub — ready for real implementation
# ═══════════════════════════════════════════════════════════════════════


class Neo4jGraphStore:
    """GraphStore backed by Neo4j. Placeholder with connection setup.

    To activate: set GRAPH_STORE_BACKEND=neo4j and configure Neo4j env vars.
    Requires `pip install neo4j` (not in default requirements).
    """

    def __init__(self, uri: str, user: str, password: str, database: str) -> None:
        self._uri = uri
        self._user = user
        self._password = password
        self._database = database
        self._driver = None

    async def _get_driver(self):
        if self._driver is None:
            try:
                from neo4j import AsyncGraphDatabase
                self._driver = AsyncGraphDatabase.driver(
                    self._uri, auth=(self._user, self._password),
                )
            except ImportError as exc:
                raise RuntimeError(
                    "neo4j package not installed. "
                    "Run: pip install neo4j"
                ) from exc
        return self._driver

    async def upsert_entity(self, tenant_id: UUID, entity: Entity) -> Entity:
        raise NotImplementedError("Neo4j upsert_entity — implement with Cypher MERGE")

    async def upsert_relationship(
        self, tenant_id: UUID, relationship: Relationship,
    ) -> Relationship:
        raise NotImplementedError("Neo4j upsert_relationship — implement with Cypher MERGE")

    async def upsert_community(
        self, tenant_id: UUID, community: Community,
    ) -> Community:
        raise NotImplementedError("Neo4j upsert_community")

    async def assign_entity_community(
        self, entity_id: UUID, community_id: UUID,
    ) -> None:
        raise NotImplementedError("Neo4j assign_entity_community")

    async def get_entities_by_name(
        self, tenant_id: UUID, names: list[str],
    ) -> list[Entity]:
        raise NotImplementedError("Neo4j get_entities_by_name")

    async def search_entities_by_embedding(
        self, tenant_id: UUID, query_embedding: list[float],
        *, top_k: int = 10, score_threshold: float = 0.3,
    ) -> list[tuple[Entity, float]]:
        raise NotImplementedError("Neo4j search_entities_by_embedding")

    async def get_entity_neighbourhood(
        self, tenant_id: UUID, entity_ids: list[UUID],
        *, hops: int = 2, max_entities: int = 20,
    ) -> GraphNeighbourhood:
        raise NotImplementedError("Neo4j get_entity_neighbourhood — use MATCH path pattern")

    async def get_all_entities(self, tenant_id: UUID) -> list[Entity]:
        raise NotImplementedError("Neo4j get_all_entities")

    async def get_all_relationships(self, tenant_id: UUID) -> list[Relationship]:
        raise NotImplementedError("Neo4j get_all_relationships")

    async def search_communities_by_embedding(
        self, tenant_id: UUID, query_embedding: list[float],
        *, top_k: int = 10,
    ) -> list[tuple[Community, float]]:
        raise NotImplementedError("Neo4j search_communities_by_embedding")

    async def delete_entities_for_document(
        self, tenant_id: UUID, document_id: UUID,
    ) -> int:
        raise NotImplementedError("Neo4j delete_entities_for_document")
