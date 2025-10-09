"""LLM-powered concept extraction from transcript groups."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any, Optional

from dotenv import load_dotenv
import openai

from src.domain.concept import Concept, ConceptMention, ConceptType, ExtractedConcepts

# Load environment variables
load_dotenv()


class ConceptExtractor:
    """Extract concepts from transcript groups using LLM."""

    # Prompt template for concept extraction
    EXTRACTION_PROMPT = """You are an expert knowledge graph curator. Analyze the following transcript segment and extract the key concepts discussed.

**Video ID:** {video_id}
**Group ID:** {group_id}
**Time Range:** {start_time:.1f}s - {end_time:.1f}s
**Duration:** {duration:.1f}s

**Transcript Text:**
{text}

**Your Task:**
Extract 5-7 key concepts from this segment. For each concept:

1. **Name**: Canonical name (2-6 words, title case)
2. **Definition**: Clear 1-3 sentence explanation
3. **Type**: One of: Person, Organization, Technology, Method, Problem, Solution, Concept, Metric, Dataset, Event, Place
4. **Importance**: Score 0.0-1.0 (how central is this to the video?)
   - 0.9-1.0: Main topic/thesis
   - 0.7-0.8: Major supporting concept
   - 0.5-0.6: Relevant detail
   - 0.3-0.4: Minor reference
5. **Confidence**: Score 0.0-1.0 (how clear/explicit is this in the text?)
   - 0.9-1.0: Explicitly named and defined
   - 0.7-0.8: Clearly implied
   - 0.5-0.6: Inferred with some ambiguity
6. **Aliases**: Alternative names/spellings (if any)

**Output Format:**
Respond ONLY with valid JSON in this exact structure:

```json
{{
  "concepts": [
    {{
      "name": "Example Concept",
      "definition": "A clear explanation of what this concept means.",
      "type": "Concept",
      "importance": 0.8,
      "confidence": 0.9,
      "aliases": ["alternative name", "another name"]
    }}
  ]
}}
```

**Guidelines:**
- Focus on substantive ideas, not trivial mentions
- Be specific and concrete in definitions
- Ensure names are concise but descriptive
- Importance reflects global significance to the entire video
- Confidence reflects clarity of extraction from THIS text
- Aliases are optional but valuable for recall
"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.3,
        base_url: Optional[str] = None,
    ):
        """Initialize the concept extractor.

        Args:
            api_key: API key (defaults to LLM_BINDING_API_KEY or OPENAI_API_KEY env var)
            model: Model to use for extraction (defaults to LLM_MODEL or gpt-4o-mini)
            temperature: Sampling temperature (lower = more consistent)
            base_url: Base URL for API (defaults to LLM_BINDING_HOST or OpenAI default)
        """
        # Support both custom LLM binding and standard OpenAI
        self.api_key = (
            api_key or os.getenv("LLM_BINDING_API_KEY") or os.getenv("OPENAI_API_KEY")
        )
        if not self.api_key:
            raise ValueError(
                "API key must be provided or set in LLM_BINDING_API_KEY/OPENAI_API_KEY env var"
            )

        # Get model from env or use default
        self.model = model or os.getenv("LLM_MODEL") or "gpt-4o-mini"

        # Get base URL from env if provided
        self.base_url = base_url or os.getenv("LLM_BINDING_HOST")

        self.temperature = temperature

        # Initialize OpenAI client with custom base_url if provided
        if self.base_url:
            self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
            print(f"✓ Initialized ConceptExtractor with model: {self.model}")
            print(f"  Using custom endpoint: {self.base_url}")
        else:
            self.client = openai.OpenAI(api_key=self.api_key)
            print(f"✓ Initialized ConceptExtractor with model: {self.model}")

    def extract_from_group(
        self,
        video_id: str,
        group_id: int,
        group_text: str,
        start_time: float,
        end_time: float,
    ) -> ExtractedConcepts:
        """Extract concepts from a single group.

        Args:
            video_id: Video identifier
            group_id: Group identifier within video
            group_text: Full text of the group
            start_time: Start timestamp (seconds)
            end_time: End timestamp (seconds)

        Returns:
            ExtractedConcepts object with all extracted concepts

        Raises:
            ExtractionError: If extraction fails
        """
        # Format the prompt
        prompt = self.EXTRACTION_PROMPT.format(
            video_id=video_id,
            group_id=group_id,
            start_time=start_time,
            end_time=end_time,
            duration=end_time - start_time,
            text=group_text,
        )

        try:
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at extracting structured knowledge from text. Always respond with valid JSON only.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=2000,
            )

            # Extract response
            raw_response = response.choices[0].message.content

            # Parse JSON response
            concepts_data = self._parse_response(raw_response)

            # Convert to Concept objects
            concepts = self._build_concepts(
                concepts_data=concepts_data,
                video_id=video_id,
                group_id=group_id,
                start_time=start_time,
                end_time=end_time,
            )

            # Create result container
            result = ExtractedConcepts(
                video_id=video_id,
                group_id=group_id,
                group_text=group_text,
                concepts=concepts,
                model_used=self.model,
            )

            return result

        except Exception as e:
            raise ExtractionError(
                f"Failed to extract concepts from group {group_id}: {e}"
            ) from e

    def _parse_response(self, raw_response: str) -> dict:
        """Parse the LLM response into structured data.

        Args:
            raw_response: Raw text from LLM

        Returns:
            Parsed JSON dictionary

        Raises:
            ExtractionError: If parsing fails
        """
        # Try to find JSON in the response (in case LLM adds extra text)
        json_match = re.search(r"\{.*\}", raw_response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
        else:
            json_str = raw_response

        try:
            data = json.loads(json_str)

            if "concepts" not in data:
                raise ExtractionError("Response missing 'concepts' key")

            if not isinstance(data["concepts"], list):
                raise ExtractionError("'concepts' must be a list")

            return data

        except json.JSONDecodeError as e:
            raise ExtractionError(f"Invalid JSON response: {e}") from e

    def _build_concepts(
        self,
        concepts_data: dict,
        video_id: str,
        group_id: int,
        start_time: float,
        end_time: float,
    ) -> list[Concept]:
        """Build Concept objects from extracted data.

        Args:
            concepts_data: Parsed JSON data
            video_id: Video identifier
            group_id: Group identifier
            start_time: Group start time
            end_time: Group end time

        Returns:
            List of Concept objects
        """
        concepts = []

        for i, concept_dict in enumerate(concepts_data["concepts"]):
            try:
                # Extract fields with validation
                name = concept_dict.get("name", "").strip()
                definition = concept_dict.get("definition", "").strip()
                type_str = concept_dict.get("type", "Concept")
                importance = float(concept_dict.get("importance", 0.5))
                confidence = float(concept_dict.get("confidence", 0.7))
                aliases = concept_dict.get("aliases", [])

                # Skip if name or definition missing
                if not name or not definition:
                    print(f"⚠️  Skipping concept {i+1}: missing name or definition")
                    continue

                # Create Concept object
                concept = Concept(
                    name=name,
                    definition=definition,
                    type=ConceptType.from_string(type_str),
                    importance=importance,
                    confidence=confidence,
                    video_id=video_id,
                    group_id=group_id,
                    first_mention_time=start_time,
                    last_mention_time=end_time,
                    mention_count=1,  # Single mention for now
                    aliases=aliases if isinstance(aliases, list) else [],
                )

                concepts.append(concept)

            except Exception as e:
                print(f"⚠️  Failed to build concept {i+1}: {e}")
                continue

        return concepts


class ExtractionError(Exception):
    """Raised when concept extraction fails."""

    pass


def main():
    """Example usage of ConceptExtractor."""

    # Sample group data
    sample_group = {
        "video_id": "HbDqLPm_2vY",
        "group_id": 0,
        "start_time": 120.5,
        "end_time": 245.8,
        "text": """
        Temporal decay penalty is a technique that reduces similarity scores between
        segments that are far apart in time. This prevents topic teleportation where
        semantically similar but temporally distant segments get incorrectly grouped.
        
        The formula uses exponential decay: sim_eff = sim * exp(-Δt / τ), where τ is
        the temporal decay constant. This preserves narrative flow while still allowing
        thematic connections when appropriate.
        """,
    }

    # Initialize extractor
    extractor = ConceptExtractor()

    # Extract concepts
    print(f"\n📝 Extracting concepts from group {sample_group['group_id']}...")
    result = extractor.extract_from_group(
        video_id=sample_group["video_id"],
        group_id=sample_group["group_id"],
        group_text=sample_group["text"],
        start_time=sample_group["start_time"],
        end_time=sample_group["end_time"],
    )

    # Display results
    print(f"\n✅ Extracted {len(result.concepts)} concepts:")
    print(f"   Average importance: {result.avg_importance:.2f}")
    print(f"   Average confidence: {result.avg_confidence:.2f}")
    print(f"   Type distribution: {result.type_distribution}")

    print("\n📊 Concepts:")
    for concept in result.concepts:
        print(f"\n  • {concept.name} ({concept.type.value})")
        print(
            f"    Importance: {concept.importance:.2f} | Confidence: {concept.confidence:.2f}"
        )
        print(f"    Definition: {concept.definition[:100]}...")
        if concept.aliases:
            print(f"    Aliases: {', '.join(concept.aliases)}")

    # Validate
    is_valid, issues = result.validate()
    if is_valid:
        print("\n✅ Validation passed")
    else:
        print(f"\n⚠️  Validation issues:")
        for issue in issues:
            print(f"  - {issue}")


if __name__ == "__main__":
    main()
