import difflib


def simple_merge(txt1, txt2):
    """Merges two texts"""
    differ = difflib.Differ(charjunk=difflib.IS_CHARACTER_JUNK)
    diff = differ.compare(txt1.splitlines(1), txt2.splitlines(1))

    return "".join([_l[2:] for _l in diff])
