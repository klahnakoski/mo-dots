import re
import sys

from mo_future import flatten

from mo_dots.utils import get_logger, is_missing, is_null

ESCAPE_DOTS1 = re.compile(r"(^\.|\.$)")  # DOTS AT START/END
ESCAPE_DOTS2 = re.compile(r"(?<!^)\.(?!$)")  # INTERNAL DOTS
ILLEGAL_DOTS = re.compile(r"[^.]\.(?:\.\.)+(?!\.)")  # ODD DOTS ARE NOT ALLOWED
UNESCAPE_DOTS = re.compile(r"\x08|(?:\.\.)")  # ENCODED DOTS


def literal_field(field):
    """
    RETURN SAME WITH DOTS (`.`) ESCAPED
    """
    try:
        return ESCAPE_DOTS2.sub("..", ESCAPE_DOTS1.sub("\b", field))
    except Exception as e:
        get_logger().error("bad literal", cause=e)


def unliteral_field(field):
    """
    DUE TO PATHOLOGY IN MY CODE WE HAVE A path WITH ESCAPED DOTS BUT WE WANT OT USE IT ON A dict, NOT A Data
    a = dict()
    b = Data(a)
    a[unliteral_field(k)]==b[k] (for all k)

    :param field: THE STRING TO DE-literal IZE
    :return: SIMPLER STRING
    """
    return UNESCAPE_DOTS.sub(".", field)


def tail_field(field):
    """
    RETURN THE FIRST STEP IN PATH, ALONG WITH THE REMAINING TAIL
    IN (first, rest) PAIR
    """
    if field == "." or is_missing(field):
        return ".", "."
    elif "." in field:
        path = split_field(field)
        if path[0].startswith("."):
            return path[0], join_field(path[1:])
        return literal_field(path[0]), join_field(path[1:])
    else:
        return field, "."


def split_field(field):
    """
    SPLIT field ON DOTS; "." OR MISSING MEANS NO STEPS
    """
    if field == "." or is_missing(field):
        return []
    if "..." in field and ILLEGAL_DOTS.search(field):
        get_logger().error("Odd number of dots is not allowed")
    if field.startswith(".."):
        remainder = field.lstrip(".")
        back = len(field) - len(remainder) - 1
        return [".."] * back + [k.replace("\b", ".") for k in remainder.replace("..", "\b").split(".") if k]
    return [k.replace("\b", ".") for k in field.replace("..", "\b").split(".") if k]


def join_field(path):
    """
    RETURN field SEQUENCE AS STRING
    """
    prefix = ""
    steps = []
    for step in path:
        if step != "..":
            steps.append(step)
        elif steps:
            steps.pop()
        else:
            prefix += "."
    if not (prefix or steps):
        return "."
    return ("." if prefix else "") + prefix + ".".join(literal_field(f) for f in steps)


def concat_field(*fields):
    return join_field(flatten(split_field(f) for f in fields))


def startswith_field(field, prefix):
    """
    RETURN True IF field PATH STRING STARTS WITH prefix PATH STRING
    """
    if prefix == None:
        return False
    if prefix.startswith("."):
        return len(prefix) == 1

    if field.startswith(prefix):
        lp = len(prefix)
        if len(field) == len(prefix) or field[lp] in (".", "\b") and field[lp + 1 : lp + 2] not in (".", "\b"):
            return True
    return False


def endswith_field(field, suffix):
    """
    RETURN True IF field PATH STRING ENDS WITH suffix PATH STRING
    """
    if is_null(suffix):
        return False
    if suffix == ".":
        return True

    if field.endswith(suffix):
        ls = len(suffix)
        if len(field) == ls or field[-ls - 1] in (".", "\b") and field[-ls - 2 : -ls - 1] not in (".", "\b"):
            return True
    return False


def relative_field(field, parent):
    """
    RETURN field PATH WITH RESPECT TO parent
    """
    if parent == ".":
        return field

    field_path = split_field(field)
    parent_path = split_field(parent)
    common = 0
    for f, p in zip(field_path, parent_path):
        if f != p:
            break
        common += 1

    tail = join_field(field_path[common:])
    if len(parent_path) <= common:
        return tail

    dots = "." * (len(parent_path) - common)
    if tail == ".":
        return "." + dots
    else:
        return "." + dots + tail
