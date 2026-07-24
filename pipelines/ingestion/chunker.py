import re
from dataclasses import dataclass

import tiktoken


@dataclass
class Chunk:
    content: str
    metadata: dict


class Chunker:

    def __init__(self):
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def _token_count(self, text: str) -> int:
        return len(self.encoding.encode(text))

    def fixed_size(
        self,
        text: str,
        chunk_size: int = 512,
        overlap: int = 64,
    ) -> list[Chunk]:

        sentences = re.split(r'(?<=[.!?])\s+', text)

        chunks = []
        current = ""

        for sentence in sentences:

            candidate = (
                sentence
                if not current
                else current + " " + sentence
            )

            if self._token_count(candidate) <= chunk_size:
                current = candidate
            else:
                if current:
                    chunks.append(
                        Chunk(
                            content=current,
                            metadata={}
                        )
                    )
                current = sentence

        if current:
            chunks.append(
                Chunk(
                    content=current,
                    metadata={}
                )
            )

        return chunks

    def semantic(self, text: str) -> list[Chunk]:
        # Placeholder implementation
        return self.fixed_size(text)

    def hierarchical(self, sections: list[dict]) -> list[Chunk]:

        chunks = []

        for section in sections:

            parent = section.get("title", "")

            chunks.append(
                Chunk(
                    content=section.get("content", ""),
                    metadata={
                        "parent": parent,
                        "children": section.get("children", [])
                    },
                )
            )

        return chunks

    def select_strategy(
        self,
        content_type: str,
        has_headings: bool = False,
        page_count: int = 0,
    ):

        if content_type == "table":
            return self.fixed_size

        if has_headings:
            return self.hierarchical

        if page_count > 50:
            return self.semantic

        return self.fixed_size