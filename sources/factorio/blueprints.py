"""blueprints.py
Routines for decoding, inspecting, manipulating, and re-encoding Factorio
blueprints.
"""

import base64
import collections
import json
import zlib


class EncodedBlob(object):
    """one Factorio json->gzip->base64 encoded blob"""

    def __init__(self, data=None, version_byte='0'):
        """Default Constructor, that also takes raw data, or acts as a copy constructor"""
        if issubclass(type(data), EncodedBlob):
            self.data = data.data.copy()
            self.version_byte = data.version_byte
        else:
            self.data = data or {}
            self.version_byte = version_byte

    def __getattr__(self, attr):
        """
        Generically provide access to blueprint.data.blueprint.entities etc
        WARNING:  These are read only, and will silently fail if a user attempts to modify them!
        """
        return self.inner_data.get(attr)

    def update(self, key, value):
        """Since getattr is read only, use this to update data"""
        self.data[self.data_type].update({key:value})

    @property
    def data_type(self):
        """
        Factorio blueprints (and books), have a root object, under which everything is nested.
        This gives the name of that object.
        """
        data_type, _ = next(iter(self.data.items()))
        return data_type

    @property
    def inner_data(self):
        """
        Factorio blueprints (and books), have a root object, under which everything is nested.
        This gives access to everything under that root object without having to know its name.
        WARNING:  This is a read only copy, and will silently fail if a user attempts to modify it!
        """
        return self.data[self.data_type]

    @classmethod
    def from_exchange_string(cls, exchange_str):
        version_byte = exchange_str[0]
        decoded = base64.b64decode(exchange_str[1:])
        json_str = zlib.decompress(decoded).decode("utf8")    #Convert from bytes to str
        data = json.loads(json_str, object_pairs_hook=collections.OrderedDict)
        return cls(data = data, version_byte = version_byte)

    @classmethod
    def from_exchange_file(cls, filename):
        return cls.from_exchange_string(open(filename).read().strip())

    @classmethod
    def from_json_string(cls, json_str):
        data = json.loads(json_str, object_pairs_hook=collections.OrderedDict)
        version_byte = data.pop("version_byte", None)
        return cls(data = data, version_byte = version_byte)

    @classmethod
    def from_json_file(cls, filename):
        return cls.from_json_string(open(filename, encoding="utf-8").read().strip())

    def to_exchange_string(self, **kwargs):
        if self.version_byte is None:
            raise RuntimeError(
		"Attempted to convert to exchange string with no version_byte")
        json_str = self.to_json_string(**kwargs)
        compressed = zlib.compress(json_str.encode("utf-8"), 9)
        encoded = base64.b64encode(compressed)
        return self.version_byte + encoded.decode()

    def to_exchange_file(self, filename):
        open(filename, "w").write(self.to_exchange_string())

    def to_json_string(self, **kwargs):
        data = self.data.copy()
        if self.version_byte is not None:
            data["version_byte"] = self.version_byte
        json_str = json.dumps(
            data,
            separators=(",", ":"),
            ensure_ascii=False,
            indent=2,
            **kwargs
        )
        return json_str

    def to_json_file(self, filename, **kwargs):
        open(filename, "w", encoding="utf-8").write(self.to_json_string(**kwargs))

    def set_name(self, new_name):
        """Set the blueprint/book's name"""
        self.data[self.data_type]['label'] = new_name

class Blueprint(EncodedBlob):
    """one Factorio blueprint"""

    def remove_entity_numbers(self):
        """Remove blueprint.data["blueprint"]["entities"][*]["entity_number"]"""
        next_number = 1
        for entity in self.entities:
            number = entity.pop("entity_number", None)
            # replace_entity_numbers assumes sequential numbers starting at 1
            # this assert will trigger bug reports if that assumption is wrong
            assert number == next_number or number == None
            next_number = next_number + 1

    def replace_entity_numbers(self):
        number = 1
        for entity in self.entities:
            entity["entity_number"] = number
            number = number + 1

    def materials(self):
        """Totals of each entity contained in the blueprint."""
        mats = {}
        for ent in self.entities:
            name = ent["name"]
            mats[name] = mats.setdefault(name, 0) + 1
        return mats

class BlueprintBook(EncodedBlob):
    """one Factorio blueprint book, containing zero or more blueprints"""

    def __init__(self, *args, **kwargs):
        super(BlueprintBook, self).__init__(*args, **kwargs)
        #Handle creating an empty blueprint book
        if not self.data:
            self.data = collections.OrderedDict()
            self.data["blueprint_book"] = collections.OrderedDict()
            book=self.data["blueprint_book"]
            book['item'] = "blueprint-book"
            book['blueprints'] = []
            book['active_index'] = 0
            book['label'] = "Empty Blueprint Book"
            book['version'] = 0
        self.objectify_blueprints()

    def objectify_blueprints(self):
        # convert internal blueprint dicts to Blueprint objects
        self.data["blueprint_book"]["blueprints"] = list(map(
            lambda data: Blueprint(data=data, version_byte=self.version_byte),
            self.data["blueprint_book"]["blueprints"]
        ))

    def to_json_string(self, **kwargs):
        # convert internal Blueprint objects back to dicts for serialization
        self.data["blueprint_book"]["blueprints"] = list(map(
            lambda blueprint: blueprint.data,
            self.data["blueprint_book"]["blueprints"]
        ))
        json_str = super(BlueprintBook, self).to_json_string(**kwargs)
        self.objectify_blueprints()
        return json_str

    def remove_indexes(self):
        """Remove self.data["blueprint_book"]["blueprints"][*]["index"]"""
        next_number = 0
        for blueprint in self.blueprints:
            number = blueprint.data.pop("index", None)
            # replace_indexes assumes sequential numbers starting at 0
            # this assert will trigger bug reports if that assumption is wrong
            assert number == next_number or number == None
            next_number = next_number + 1

    def replace_indexes(self):
        number = 0
        for blueprint in self.blueprints:
            blueprint.data["index"] = number
            number = number + 1

    def add_blueprint(self, in_blueprint):
        """Add a blueprint to the book"""
        self.data["blueprint_book"]["blueprints"].append(in_blueprint)
