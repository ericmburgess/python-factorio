"""blueprints.py

Routines for decoding, inspecting, manipulating, and re-encoding Factorio
blueprints.
"""


import base64
import collections
import json
import zlib


class Blueprint(object):
    """Factorio blueprint class.

    Args:
        version_byte: The first byte of the exchange string. Probably indicates
            the blueprint exchange protocol version.
        data: A mapping containing the blueprint data decoded from the exchange
            string.
        exch_str: The original exchange string. Optional.
        json_str: The originally decoded JSON string. Optional.
    """

    def __init__(self, version_byte, data, exch_str="", json_str=""):
        self.version_byte = version_byte
        self.data = data
        self.exch_str = exch_str
        self.json_str = json_str
        self.version = self.data["blueprint"]["version"]
        self.entities = self.data["blueprint"]["entities"]
        self.icons = self.data["blueprint"]["icons"]


    def materials(self):
        """Totals of each entity contained in the blueprint."""
        mats = {}
        for ent in self.entities:
            name = ent["name"]
            mats[name] = mats.setdefault(name, 0) + 1
        return mats



def loads(exchange_str):
    """Load a blueprint from an exchange string.

    Args:
        exchange_str: A Factorio exchange string.

    Returns: a Blueprint instance.
    """
    version_byte = exchange_str[0]
    decoded = base64.b64decode(exchange_str[1:])
    json_str = zlib.decompress(decoded)
    data = json.loads(json_str, object_pairs_hook=collections.OrderedDict)
    return Blueprint(
        version_byte, data, exch_str=exchange_str, json_str=json_str)

def load(infile):
    """Load a blueprint from a file.

    Args:
        infile: name of the file to read from.

    Returns: a Blueprint instance.
    """
    return loads(open(infile).read().strip())


def dumps(bprint):
    """Produce an exchange string for a blueprint.

    Args:
        bprint: a Blueprint instance.

    Returns: A Factorio exchange string.
    """
    json_str = json.dumps(
        bprint.data, separators=(",", ":"), ensure_ascii=False).encode("utf8")
    compressed = zlib.compress(json_str, 9)
    encoded = base64.b64encode(compressed)
    return bprint.version_byte + encoded


def dump(bprint, outfile):
    """Write a blueprint exchange string to a file.

    Args:
        bprint: a Blueprint instance.
    """
    open(outfile, "w").write(dumps(bprint))
