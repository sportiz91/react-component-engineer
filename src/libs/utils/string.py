def wrap_text(text: str, max_width: int = 120) -> str:
    lines = []
    for paragraph in text.split("\n"):
        line = []
        length = 0
        for word in paragraph.split():
            if length + len(word) + 1 > max_width:
                lines.append(" ".join(line))
                line = [word]
                length = len(word)
            else:
                line.append(word)
                length += len(word) + 1
        lines.append(" ".join(line))
    return "\n".join(lines)
