from typing import List
import re


import textwrap


def wrap_text(text: str, max_width: int = 120) -> str:
    lines: List[str] = text.split("\n")
    wrapped_lines = []

    for line in lines:
        if line.strip() == "":
            wrapped_lines.append(line)
            continue

        indent: int = get_function_indent(line)
        indent_str = " " * indent

        wrapped: List[str] = textwrap.wrap(line.strip(), width=max_width - indent, break_long_words=False, replace_whitespace=False)

        wrapped_lines.extend(indent_str + subline for subline in wrapped)

    return "\n".join(wrapped_lines)


def get_function_indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def write_indented_content(content: str, indent_level: int = 2) -> str:
    content: str = content.strip()

    indented_lines: list[str] = [" " * indent_level + line if line.strip() != "" else "" for line in content.splitlines()]

    indented_content: str = "\n".join(indented_lines)

    return indented_content


def remove_non_printable_characters(text: str) -> str:
    return re.sub(r"[^\x20-\x7E\n\r\t]", "", text)
