"""Shared dataclasses for the GraphRAG layer.

These are the in-memory representations used throughout the graph pipeline.
They map cleanly to the SQLAlchemy models but are decoupled for testability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID


@dataclass
class Entity:
    """An extracted entity (graph node)."""

    name: str
    entity_type: str
    description: str = ""
    source_chunk_ids: list[dict] = field(default_factory=list)
    id: UUID | None = None
    embedding: list[float] | None = None
    community_id: UUID | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class Relationship:
    """An extracted relationship (graph edge)."""

    source_entity: str  # name (resolved to ID at store time)
    target_entity: str  # name
    relationship_type: str
    description: str = ""
    weight: float = 1.0
    source_chunk_ids: list[dict] = field(default_factory=list)
    id: UUID | None = None
    source_entity_id: UUID | None = None
    target_entity_id: UUID | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ExtractionResult:
    """Result from the entity/relationship extraction step."""

    entities: list[Entity]
    relationships: list[Relationship]
    chunk_id: UUID | None = None
    document_id: UUID | None = None


@dataclass
class Community:
    """A detected entity community with its summary."""

    id: UUID | None = None
    name: str = ""
    level: int = 0
    entity_ids: list[UUID] = field(default_factory=list)
    entity_names: list[str] = field(default_factory=list)
    relationship_count: int = 0
    summary: str = ""
    summary_embedding: list[float] | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class GraphNeighbourhood:
    """Result from a local graph search — entities + relationships around a seed."""

    seed_entities: list[Entity]
    neighbour_entities: list[Entity]
    relationships: list[Relationship]
    source_chunks: list[dict] = field(default_factory=list)

    @property
    def all_entities(self) -> list[Entity]:
        seen = {e.name for e in self.seed_entities}
        result = list(self.seed_entities)
        for e in self.neighbour_entities:
            if e.name not in seen:
                seen.add(e.name)
                result.append(e)
        return result

    def to_context_text(self) -> str:
        """Render neighbourhood as natural-language context for the LLM."""
        lines: list[str] = []
        lines.append("=== Entity Knowledge Graph Context ===")
        lines.append("")
        for e in self.all_entities:
            lines.append(f"[{e.entity_type}] {e.name}: {e.description}")
        lines.append("")
        lines.append("Relationships:")
        for r in self.relationships:
            lines.append(
                f"  {r.source_entity} --[{r.relationship_type}]--> "
                f"{r.target_entity}: {r.description}"
            )
        return "\n".join(lines)


@dataclass
class CommunitySearchResult:
    """Result from a global community-summary search."""

    communities: list[Community]
    total_found: int = 0

    def to_context_text(self) -> str:
        """Render community summaries as context for the LLM."""
        lines: list[str] = []
        lines.append("=== Community Summaries ===")
        lines.append("")
        for c in self.communities:
            lines.append(f"## {c.name} (level {c.level})")
            lines.append(c.summary)
            lines.append("")
        return "\n".join(lines)


@dataclass
class GraphSearchResult:
    """Combined result from GraphRAG retrieval (local + global)."""

    local: GraphNeighbourhood | None = None
    global_: CommunitySearchResult | None = None
    strategy: str = "graph_local"
    graph_ms: int = 0

    def to_context_text(self) -> str:
        parts: list[str] = []
        if self.local:
            parts.append(self.local.to_context_text())
        if self.global_:
            parts.append(self.global_.to_context_text())
        return "\n\n".join(parts)
