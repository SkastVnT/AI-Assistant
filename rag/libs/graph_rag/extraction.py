"""Entity and relationship extraction from text chunks using LLM.

Sends each chunk to the LLM with a structured extraction prompt.
Returns typed Entity + Relationship dataclasses ready for storage.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from libs.graph_rag.types import Entity, ExtractionResult, Relationship

if TYPE_CHECKING:
    from libs.core.providers.base import LLMProvider

logger = logging.getLogger("rag.graph_rag.extraction")

# ═══════════════════════════════════════════════════════════════════════
# Extraction prompt
# ═══════════════════════════════════════════════════════════════════════

ENTITY_EXTRACTION_SYSTEM = """\
You are an expert knowledge-graph builder. Given a text chunk, extract \
named entities and the relationships between them.

ENTITY TYPES (use one of these):
  PERSON, ORGANIZATION, LOCATION, CONCEPT, TECHNOLOGY, EVENT, DOCUMENT, PRODUCT, OTHER

RELATIONSHIP TYPES (use one of these):
  USES, PART_OF, RELATED_TO, CREATED_BY, LOCATED_IN, WORKS_FOR, MANAGES, \
  DEPENDS_ON, CONTAINS, IMPLEMENTS, DERIVED_FROM, INTERACTS_WITH, OTHER

RULES:
1. Entity names should be canonical — use the most complete form of the name.
2. Descriptions should be short (one sentence).
3. Only extract entities and relationships that are clearly stated.
4. Merge duplicate entities (same name, different mentions).
5. Every relationship must reference entities that appear in the entity list.

OUTPUT FORMAT — respond with valid JSON only, no markdown fences:
{
  "entities": [
    {"name": "...", "type": "...", "description": "..."}
  ],
  "relationships": [
    {"source": "...", "target": "...", "type": "...", "description": "..."}
  ]
}
"""

ENTITY_EXTRACTION_PROMPT = """\
Extract entities and relationships from the following text chunk.
Return ONLY the JSON object described in the system prompt.

--- TEXT ---
{chunk_text}
--- END TEXT ---
"""


# ═══════════════════════════════════════════════════════════════════════
# Extraction function
# ═══════════════════════════════════════════════════════════════════════


async def extract_entities_and_relationships(
    llm: LLMProvider,
    chunk_text: str,
    *,
    chunk_id: str | None = None,
    document_id: str | None = None,
    max_entities: int = 20,
    max_relationships: int = 30,
    temperature: float = 0.0,
) -> ExtractionResult:
    """Extract entities and relationships from a single text chunk.

    Parameters
    ----------
    llm:
        An LLMProvider for completions.
    chunk_text:
        The raw text of the chunk.
    chunk_id, document_id:
        Optional identifiers to attach to source_chunk_ids.
    max_entities, max_relationships:
        Caps to prevent runaway extraction.
    temperature:
        Sampling temperature (0 = deterministic).

    Returns
    -------
    ExtractionResult with parsed entities and relationships.
    """
    prompt = ENTITY_EXTRACTION_PROMPT.format(chunk_text=chunk_text)

    raw = await llm.complete(
        prompt,
        system=ENTITY_EXTRACTION_SYSTEM,
        temperature=temperature,
        max_tokens=4096,
    )

    entities, relationships = _parse_extraction_response(
        raw,
        chunk_id=chunk_id,
        document_id=document_id,
        max_entities=max_entities,
        max_relationships=max_relationships,
    )

    return ExtractionResult(
        entities=entities,
        relationships=relationships,
        chunk_id=chunk_id,
        document_id=document_id,
    )


# ═══════════════════════════════════════════════════════════════════════
# Response parsing
# ═══════════════════════════════════════════════════════════════════════

VALID_ENTITY_TYPES = frozenset({
    "PERSON", "ORGANIZATION", "LOCATION", "CONCEPT",
    "TECHNOLOGY", "EVENT", "DOCUMENT", "PRODUCT", "OTHER",
})

VALID_RELATIONSHIP_TYPES = frozenset({
    "USES", "PART_OF", "RELATED_TO", "CREATED_BY", "LOCATED_IN",
    "WORKS_FOR", "MANAGES", "DEPENDS_ON", "CONTAINS", "IMPLEMENTS",
    "DERIVED_FROM", "INTERACTS_WITH", "OTHER",
})


def _parse_extraction_response(
    raw: str,
    *,
    chunk_id: str | None,
    document_id: str | None,
    max_entities: int,
    max_relationships: int,
) -> tuple[list[Entity], list[Relationship]]:
    """Parse the JSON response from the LLM.

    Resilient to markdown fences, trailing commas, etc.
    """
    # Strip markdown fences if present
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("extraction_parse_error: could not parse LLM JSON output")
        return [], []

    source_ref = []
    if chunk_id or document_id:
        source_ref = [{"chunk_id": chunk_id, "document_id": document_id}]

    # Parse entities
    raw_entities = data.get("entities", [])
    if not isinstance(raw_entities, list):
        raw_entities = []
    entities: list[Entity] = []
    seen_names: set[str] = set()
    for item in raw_entities[:max_entities]:
        name = str(item.get("name", "")).strip()
        etype = str(item.get("type", "OTHER")).strip().upper()
        if not name:
            continue
        # Deduplicate within this chunk
        key = f"{name}|{etype}"
        if key in seen_names:
            continue
        seen_names.add(key)
        if etype not in VALID_ENTITY_TYPES:
            etype = "OTHER"
        entities.append(Entity(
            name=name,
            entity_type=etype,
            description=str(item.get("description", "")),
            source_chunk_ids=source_ref,
        ))

    # Parse relationships
    raw_rels = data.get("relationships", [])
    if not isinstance(raw_rels, list):
        raw_rels = []
    entity_names = {e.name for e in entities}
    relationships: list[Relationship] = []
    for item in raw_rels[:max_relationships]:
        source = str(item.get("source", "")).strip()
        target = str(item.get("target", "")).strip()
        rtype = str(item.get("type", "RELATED_TO")).strip().upper()
        if not source or not target:
            continue
        if source not in entity_names or target not in entity_names:
            logger.debug(
                "skip_relationship: %s -> %s (entity not found)", source, target,
            )
            continue
        if rtype not in VALID_RELATIONSHIP_TYPES:
            rtype = "OTHER"
        relationships.append(Relationship(
            source_entity=source,
            target_entity=target,
            relationship_type=rtype,
            description=str(item.get("description", "")),
            source_chunk_ids=source_ref,
        ))

    logger.info(
        "extracted chunk=%s entities=%d relationships=%d",
        chunk_id, len(entities), len(relationships),
    )
    return entities, relationships
