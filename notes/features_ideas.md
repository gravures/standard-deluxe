# Features Ideas

## A Generic Lookup Function

see also: ../tomlraider/src/tomlraider/cli.py

```python
def lookup(path: str, namespace: Mapping[str, object], default: _T) -> _T:
    """Look up for property in namespace."""
    key = None
    parts = path.split(".")

    try:
        for key in parts[:-1]:
            namespace = namespace[key]  # pyright: ignore[reportAssignmentType]
    except KeyError as err:
        msg = f"pyproject does not contain a <{key}> section."
        raise LookupError(msg) from err
    else:
        try:
            result = namespace[parts[-1]]
        except LookupError:
            result = default
    return cast(_T, result)
```

```python
def validate_fields(fields: tuple[Field[Any], ...]) -> None:
    for field in fields:
        _validate_field(
            getattr(dataclass, field.name),
            cast("Annot", field.type),
        )


def _flatten_types(types: Annot | tuple[Annot, ...]) -> tuple[type, ...]:
    annotations: tuple[Annot, ...] = types if isinstance(types, tuple) else (types,)
    return tuple(get_origin(type_) or type_ for type_ in get_args(types))


def _validate_field(attr: object, type_: Annot) -> None:
    if isinstance(type_, type):  # atomic types
        assert isinstance(attr, type_)
    elif isinstance(type_, UnionType):  # union
        union = _flatten_types(type_)
        assert isinstance(attr, union)
    elif type__ := get_origin(type_):  # type_ is a GenericAlias
        assert isinstance(attr, type__)
        args = get_args(type__)
```

## Dataclass attributes validation

```python
@dataclass
class Validator:
    def __post_init__(self) -> None:
        self._validate_fields()

    def _validate_fields(self) -> None:
        for field in fields(self):
            self._validate_field(
                getattr(self, field.name),
                cast("type | GenericAlias", field.type),
            )

    def _validate_field(self, attr: object, typ: type | GenericAlias | UnionType) -> None:
        if isinstance(typ, type):
            assert isinstance(attr, typ)
        elif isinstance(typ, UnionType):
            pass
        elif typ := get_origin(typ):
            assert isinstance(attr, typ)
            args = get_args(typ)

```
