"""Model composition.

This module contains utilities for merging multiple modeling steps into a single pipeline. Although
pipelines are not the only way to process a stream of data, we highly encourage you to use them.

"""
from .func import FuncTransformer
from .pipeline import Pipeline
from .rename import Renamer
from .union import TransformerUnion
from .select import Discard
from .select import Select


__all__ = [
    'Discard',
    'FuncTransformer',
    'Pipeline',
    'Renamer',
    'TransformerUnion',
    'Select'
]
