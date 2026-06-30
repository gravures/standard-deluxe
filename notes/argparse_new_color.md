# PrettyParser and Python 3.14 color kwarg

Python 3.14 added two new keyword-only parameters to ArgumentParser.__init__():

- color: bool = True — controls ANSI color in help output
- suggest_on_error: bool = False — suggests corrections on typos

The critical path that triggers the bug:

Parser.add_subparsers()
  → creates _SubParsersAction
    → sets action._color = self.color (which is True from ArgumentParser.__init__)

SubparsersAction.add_parser("name")
  → injects: kwargs['color'] = self._color (which is True)
  → calls: self._parser_class(**kwargs)
  → becomes: PrettyParser(prog='...', color=True)
  → TypeError: PrettyParser.__init__() got an unexpected keyword argument 'color'

On Python 3.13 and earlier, add_parser does NOT inject color — this kwarg simply doesn't exist.

## What Python 3.14 does with color

The color parameter flows through the entire help formatting pipeline:

1. ArgumentParser.__init__: stores self.color = color
2. add_subparsers: propagates action._color = self.color to the subparsers action
3. _SubParsersAction.add_parser: injects kwargs['color'] = self._color when creating child parsers (THIS IS THE BUG)
4. ArgumentParser._get_formatter: calls formatter._set_color(self.color) to configure the stdlib _theme and _decolor on the formatter
5. HelpFormatter._set_color: imports _colorize, sets up self._theme (ANSI codes for summary options, labels, etc.) and self._decolor (a function to strip ANSI for width calculations)
Why PrettyHelpFormatter is NOT affected
- PrettyHelpFormatter.__init__ only receives prog=... from add_subparsers — no color kwarg
- HelpFormatter.__init__ in 3.14 defaults color=True, so _set_color(True) runs normally
- Color override happens via _get_formatter() → formatter._set_color(self.color), which is separate from construction
- The stdlib _theme (used by _get_actions_usage_parts) coexists with AnsiHelpFormatter.styles (used by _ansi_style) — they serve different purposes

## Compatibility Considerations

Aspect	Python 3.11-3.13	Python 3.14+
ArgumentParser.__init__ color param	Does not exist	color=True
HelpFormatter.__init__ color param	Does not exist	color=True
_SubParsersAction.add_parser injects color	No	Yes (self._color)
_SubParsersAction._color attr	Does not exist	Hardcoded True in __init__, then set to self.color by add_subparsers
_set_color() on formatter	Does not exist	Sets _theme + _decolor
self.suggest_on_error	Does not exist	False
Proposed Fix
Add color (and suggest_on_error for future-proofing) as accepted parameters in PrettyParser.__init__, forwarding them to super().__init__() only on Python 3.14+ where the base class accepts them:

```PrettyParserthon
import sys

def __init__(
    self,
    prog: str,
    ...
    shell_completion: bool = False,
    **_extra: Any,  # absorb Python 3.14+ kwargs (color, suggest_on_error)
) -> None:
    ...
    super().__init__(
        prog=prog,
        ...
        exit_on_error=exit_on_error,
        **_extra,  # forwarded to base class (no-op on 3.11-3.13 if empty)
    )
```

However, there's a subtlety with **_extra: if a user passes `color=False` on
 Python 3.11, it would be forwarded to super().__init__() which doesn't
accept it. A safer approach will be:

```python
import sys

# Accept explicitly, forward conditionally
def __init__(
    self,
    ...
    shell_completion: bool = False,
    color: bool = True,
) -> None:
    ...
    kwargs: dict[str, Any] = dict(
        prog=prog,
        ...
        exit_on_error=exit_on_error,
    )
    if sys.version_info >= (3, 14):
        kwargs["color"] = color
    super().__init__(**kwargs)
```

Trade-off: The `**_extra approach` is simpler and automatically handles future
kwargs, but sacrifices type safety on older Pythons. The explicit approach is
safer but requires maintenance when new params are added to the stdlib.

Recommendation: Use **_extra with a runtime check, because:

1. add_parser is the only caller that injects unknown kwargs (and only color on 3.14)
2. Users rarely call PrettyParser(color=...) directly — they set color via the formatter
3. Future Python versions may add more kwargs — **_extra absorbs them without code changes
4. On 3.11-3.13, _extra will always be empty (no code path injects extra kwargs)
