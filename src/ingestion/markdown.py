"""Markdown document parsing."""

import re
from pathlib import Path

from ..models import ParsedDocument, Section, SourceType


def extract_title(content: str) -> str:
    """Extract the title from markdown content (first H1)."""
    match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    # Fallback: first line
    first_line = content.strip().split("\n")[0]
    return first_line.lstrip("#").strip()


def extract_code_blocks(content: str) -> list[str]:
    """Extract fenced code blocks from content."""
    pattern = r"```[\w]*\n(.*?)```"
    matches = re.findall(pattern, content, re.DOTALL)
    return matches


def extract_equations(content: str) -> list[str]:
    """Extract LaTeX equations from content."""
    # Inline equations: $...$
    inline = re.findall(r"\$([^$]+)\$", content)
    # Block equations: $$...$$
    block = re.findall(r"\$\$(.+?)\$\$", content, re.DOTALL)
    return inline + block


def extract_images(content: str) -> list[str]:
    """Extract image references from content."""
    # ![alt](path)
    pattern = r"!\[([^\]]*)\]\(([^)]+)\)"
    matches = re.findall(pattern, content)
    return [path for _, path in matches]


def split_into_sections(content: str) -> list[Section]:
    """Split markdown content into sections based on headings."""
    # Pattern to match markdown headings
    heading_pattern = r"^(#{1,6})\s+(.+)$"

    lines = content.split("\n")
    sections: list[Section] = []
    current_section: Section | None = None
    current_content: list[str] = []

    for line in lines:
        match = re.match(heading_pattern, line)
        if match:
            # Save previous section
            if current_section is not None:
                section_content = "\n".join(current_content).strip()
                current_section.content = section_content
                current_section.code_blocks = extract_code_blocks(section_content)
                current_section.equations = extract_equations(section_content)
                current_section.images = extract_images(section_content)
                sections.append(current_section)

            # Start new section
            level = len(match.group(1))
            heading = match.group(2).strip()
            current_section = Section(heading=heading, level=level, content="")
            current_content = []
        else:
            current_content.append(line)

    # Don't forget the last section
    if current_section is not None:
        section_content = "\n".join(current_content).strip()
        current_section.content = section_content
        current_section.code_blocks = extract_code_blocks(section_content)
        current_section.equations = extract_equations(section_content)
        current_section.images = extract_images(section_content)
        sections.append(current_section)
    elif current_content:
        # No headings found, treat entire content as one section
        section_content = "\n".join(current_content).strip()
        sections.append(
            Section(
                heading="Main",
                level=1,
                content=section_content,
                code_blocks=extract_code_blocks(section_content),
                equations=extract_equations(section_content),
                images=extract_images(section_content),
            )
        )

    return sections


def parse_markdown(source: str | Path) -> ParsedDocument:
    """Parse a markdown file or string into a structured document.

    Args:
        source: Either a file path or markdown content string

    Returns:
        ParsedDocument with extracted sections and metadata
    """
    source_path = ""
    is_file = False

    if isinstance(source, Path):
        is_file = True
    elif isinstance(source, str) and len(source) < 500:
        # Only check if it's a file path if the string is short enough
        try:
            is_file = Path(source).exists()
        except OSError:
            is_file = False

    if is_file:
        path = Path(source)
        source_path = str(path.absolute())
        with open(path, encoding="utf-8") as f:
            content = f.read()
    else:
        content = source
        source_path = "<string>"

    # Extract title
    title = extract_title(content)

    # Split into sections
    sections = split_into_sections(content)

    return ParsedDocument(
        title=title,
        source_type=SourceType.MARKDOWN,
        source_path=source_path,
        sections=sections,
        raw_content=content,
        metadata={
            "total_sections": len(sections),
            "total_code_blocks": sum(len(s.code_blocks) for s in sections),
            "total_equations": sum(len(s.equations) for s in sections),
            "total_images": sum(len(s.images) for s in sections),
        },
    )
