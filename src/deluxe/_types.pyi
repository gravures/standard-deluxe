from __future__ import annotations  # noqa: PYI044

from types import NotImplementedType
from typing import Any

class _UnsetMeta(type):
    def __delattr__(cls, name: str, /) -> None: ...
    def __setattr__(cls, name: str, value: Any, /) -> None: ...

UnsetType = type("UnsetType", (NotImplementedType,), {})
"""The type of the :class:`Unset` singleton.

The `Unset` singleton is design to act as a sentinel value that
can be assigned to any type and mimics `None` where possible,
while being type-checker friendly.

Example:
    >>> foo: str = None  # static type checker may complain
    >>> bar: str = Unset  # should be valid for static type checker
    >>> isinstance(bar, str)
    False
    >>> not Unset
    True
    >>> UnsetType() is Unset
    True

See Also:
    :class:`Unset`: The singleton instance of this type.
"""

Unset: UnsetType

class _Frozen: ...
