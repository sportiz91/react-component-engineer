def wrap_text(text: str, max_width: int = 120) -> str:
    paragraphs = text.split("\n")
    wrapped_paragraphs = []

    for paragraph in paragraphs:
        if paragraph.strip() == "":
            wrapped_paragraphs.append("")
            continue

        words = paragraph.split()
        lines = []
        current_line = []
        current_length = 0

        for i, word in enumerate(words):
            word_length = len(word) + (1 if current_line else 0)

            if current_length + word_length > max_width and current_line:
                lines.append(" ".join(current_line))
                current_line = []
                current_length = 0

            current_line.append(word)
            current_length += word_length

            if word[-1] in ".,:;!?" and current_length >= max_width:
                lines.append(" ".join(current_line))
                current_line = []
                current_length = 0

                if word[-1] == "." and i < len(words) - 1 and words[i + 1][0].isupper():
                    lines.append("")

        if current_line:
            lines.append(" ".join(current_line))

        wrapped_paragraphs.append("\n".join(lines))

    return "\n".join(wrapped_paragraphs)
