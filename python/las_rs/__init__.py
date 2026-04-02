"""las_rs — High-performance LAS file parser and writer."""

import json as _json

from las_rs._native import (
    HeaderItem,
    CurveItem,
    SectionItems,
    LASFile,
    read,
    LASDataError,
    LASHeaderError,
    LASUnknownUnitError,
)
from las_rs._native import reader
from las_rs import exceptions

from importlib.metadata import version as _pkg_version

__version__ = _pkg_version("las-rs")


class JSONEncoder(_json.JSONEncoder):
    """JSON encoder that handles LASFile, HeaderItem, CurveItem, SectionItems."""

    def default(self, obj):
        if hasattr(obj, "json"):
            return _json.loads(obj.json)
        return super().default(obj)


__all__ = [
    "HeaderItem",
    "CurveItem",
    "SectionItems",
    "LASFile",
    "read",
    "reader",
    "JSONEncoder",
    "LASDataError",
    "LASHeaderError",
    "LASUnknownUnitError",
]
