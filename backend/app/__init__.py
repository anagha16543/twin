# backend/app/__init__.py
"""
AI-NBA Readiness System — Backend application package.
"""

import sys
import typing

# Compatibility patch for SQLAlchemy 2.0.x on Python 3.14+
try:
    import sqlalchemy.util.typing as _sa_typing
    _orig_make_union = _sa_typing.make_union_type
    def _safe_make_union(*types):
        try:
            return _orig_make_union(*types)
        except TypeError:
            return typing.Union[types] if len(types) > 1 else (types[0] if types else typing.Any)
    _sa_typing.make_union_type = _safe_make_union
except Exception:
    pass
