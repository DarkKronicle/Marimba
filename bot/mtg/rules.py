from pathlib import Path
from bot.util.json_reader import JsonReader
import re

RULES = JsonReader(Path("./storage/rules_mtg.json"))


def string_to_section(keyword):
    match = re.search(r'\d+', keyword)
    if not match:
        return None

    m = match.group(0)
    val = int(m[0])
    val1 = int(m)
    short = keyword.replace(m, "", 1)[1:]
    if len(m) == 1:
        return [val]
    if len(short) == 0 or short[0] == " ":
        return [val, val1]
    match2 = re.search(r'\d+', short)
    if not match2:
        return [val, val1]

    m2 = match2.group(0)
    val2 = int(m2)
    short = short.replace(m2, "", 1)
    if len(short) == 0 or short[0] == ".":
        return [val, val1, val2]
    return [val, val1, val2, short[0]]


def get_section(keyword):
    section = string_to_section(keyword)
    if section is None:
        return None, None
    c = RULES.data["contents"]
    for s in string_to_section(keyword):
        s = str(s)
        if s in c:
            c = c[s]
        else:
            return None, None
    return section, c


# @TODO Add deep search which goes through all text
def lookup(keyword, *, deep=False):
    if keyword.lower() in RULES.data["glossary"]:
        return RULES.data["glossary"][keyword.lower()]