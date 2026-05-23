"""
Frontmatter parsing for the Ostraca CLI.

This module provides utilities to extract YAML-like frontmatter from
Markdown files. It handles quoted values, escaped characters, and
supports both comma-separated and YAML-array styles for tags.
"""

from typing import Tuple, Dict, Any


def extract_frontmatter(raw_content: str) -> Tuple[Dict[str, Any], str]:
    """
    Extract standard YAML frontmatter bounded by '---' from the start of a string.

    Args:
        raw_content: The full content of a Markdown file, including frontmatter.

    Returns:
        A tuple of (metadata_dict, body_content).
        - metadata_dict: Dictionary of parsed keys and values.
        - body_content: The rest of the file after the frontmatter block.
        If no frontmatter is found, returns ({}, raw_content).
    """
    # Find where the actual content starts (skip leading whitespaces/newlines)
    start_idx = 0
    n = len(raw_content)
    while start_idx < n and raw_content[start_idx].isspace():
        start_idx += 1

    if not raw_content.startswith("---", start_idx):
        return {}, raw_content

    # Find the end of the first line (the starting '---')
    first_line_end = raw_content.find('\n', start_idx)
    if first_line_end == -1:
        return {}, raw_content

    # Check if the first line is exactly '---' plus optional whitespace
    if raw_content[start_idx:first_line_end].strip() != '---':
        return {}, raw_content

    # Find the closing '---' line
    # It must be preceded by a newline and followed by a newline or end of string
    search_idx = first_line_end
    yaml_str = None
    body_content = raw_content

    while True:
        close_idx = raw_content.find('\n---', search_idx)
        if close_idx == -1:
            return {}, raw_content

        # Verify the closing '---' is on its own line
        # i.e., followed by newline or end of string (after optional whitespace)
        rem = raw_content[close_idx + 4:]
        line_end = rem.find('\n')
        if line_end == -1:
            line_end = len(rem)

        if rem[:line_end].strip() == '':
            yaml_str = raw_content[first_line_end + 1 : close_idx]
            body_content = rem[line_end + 1:] if line_end < len(rem) else ""
            break
        else:
            # Keep searching if '---' is part of other text on the line
            search_idx = close_idx + 4

    metadata: Dict[str, Any] = {}

    for line in yaml_str.strip().split('\n'):
        line = line.strip()
        if not line or ':' not in line:
            continue

        # Split only on the first colon to allow colons in values (e.g., titles)
        key, value = line.split(':', 1)
        key = key.strip()
        value = value.strip()

        # Handle quoted values (both single and double quotes)
        is_double_quoted = value.startswith('"') and value.endswith('"')
        is_single_quoted = value.startswith("'") and value.endswith("'")
        if is_double_quoted or is_single_quoted:
            value = value[1:-1]
            if is_double_quoted:
                value = value.replace('\\"', '"')

        if key == 'tags':
            # Handle YAML-style array: [tag1, tag2]
            if value.startswith('[') and value.endswith(']'):
                tags_str = value[1:-1]
                # Split by comma and strip quotes/whitespace from each tag
                metadata[key] = [
                    t.strip().strip("'").strip('"')
                    for t in tags_str.split(',') if t.strip()
                ]
            else:
                # Handle comma-separated string: tag1, tag2
                metadata[key] = [
                    t.strip()
                    for t in value.split(',') if t.strip()
                ]
        else:
            metadata[key] = value

    return metadata, body_content
