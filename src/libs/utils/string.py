import textwrap

from src.libs.utils.constants import RANDOM_STRING


# @TODO: remove this functions when working, is just to test traverse with only code used mode.
def mock_function_1():
    pass


def mock_function_2():
    pass


def mock_function_3():
    pass


def mock_function_4():
    pass


def get_random_string(length: int = 10) -> str:
    import random
    import string

    print(RANDOM_STRING)

    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def wrap_text(text: str, max_width: int = 120) -> str:
    lines = text.split("\n")
    wrapped_lines = []

    for line in lines:
        if line.strip() == "":
            wrapped_lines.append(line)
            continue

        indent = len(line) - len(line.lstrip())
        indent_str = " " * indent

        wrapped = textwrap.wrap(line.strip(), width=max_width - indent, break_long_words=False, replace_whitespace=False)

        wrapped_lines.extend(indent_str + subline for subline in wrapped)

    return "\n".join(wrapped_lines)
