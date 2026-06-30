# Async Command Decorator

## Goal

A decorator for `Command` (or subclasses) that routes `__call__` to use async
subprocess execution (`async_call`) instead of the synchronous `subprocess.run`.

This would let callers benefit from async subprocesses without explicitly
calling `async_call` and awaiting it.

## Current State

| Aspect | `__call__` (sync) | `async_call` (async) |
|--------|-------------------|----------------------|
| Implementation | `subprocess.run()` | `asyncio.subprocess.create_subprocess_exec()` |
| Returns | `str \| bytes` | `Task[Future[bytes]]` |
| Has `text` param | Yes (default `True`) | No (always bytes) |
| Has `encoding` param | Yes (default `"UTF-8"`) | No |
| Has `input` param | `str \| bytes \| None` | `bytes \| None` only |

## Key Considerations

- `asyncio.run()` raises `RuntimeError` if an event loop is already running.
  A fallback to sync subprocess is needed for that case.
- `async_call` always returns bytes; `__call__` supports text decoding via
  `text`/`encoding` params. The decorator must handle the conversion.
- The project is fully typed with `basedpyright`. The decorator must preserve
  or provide accurate type signatures.
- `async_call` returns `Task[Future[bytes]]` — a nested async result.
  A sync wrapper needs `.result()` or equivalent.

## Approach 1: `asyncio.run()` Bridge (Recommended)

A class decorator that replaces `__call__` with a synchronous method using
`asyncio.run()` internally. Falls back to the original sync `__call__` if
an event loop is already running.

```python
def async_command(cls: _C) -> _C:
    original_call = cls.__call__

    @functools.wraps(original_call)
    def __call__(
        self,
        *args: str,
        input: str | bytes | None = None,
        capture: bool = True,
        text: bool = True,
        encoding: str | None = "UTF-8",
        cwd: AnyFilePath | None = None,
        env: Mapping[str, str] | None = None,
    ) -> str | bytes:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            return original_call(
                self, *args,
                input=input, capture=capture, text=text,
                encoding=encoding, cwd=cwd, env=env,
            )

        async_input = (
            input
            if isinstance(input, (bytes, type(None)))
            else input.encode(encoding or "UTF-8")
        )
        result: bytes = asyncio.run(
            self.async_call(
                *args, input=async_input, capture=capture, cwd=cwd, env=env
            )
        )
        return result.decode(encoding or "UTF-8") if text else result

    cls.__call__ = __call__  # type: ignore[assignment]
    return cls
```

**Usage:**

```python
@async_command
class MyCommand(Command):
    pass

cmd = MyCommand("ls")
result = cmd("-la")  # Uses async subprocess internally
```

**Trade-offs:**

- (+) Non-breaking API — `cmd()` still returns `str | bytes`
- (+) Preserves `text`/`encoding` parameters
- (+) Graceful fallback when inside event loop
- (-) `asyncio.run()` creates a new event loop per call (overhead for many calls)
- (-) Can't be used inside `async def` functions (falls back to sync)
- (-) Overloaded return type needs careful handling for type checkers

## Approach 2: Coroutine `__call__`

Makes `__call__` a coroutine directly. Callers must `await` it.

```python
def async_command(cls: _C) -> _C:
    cls._sync_call = cls.__call__

    def __call__(
        self,
        *args: str,
        input: bytes | None = None,
        capture: bool = True,
        cwd: AnyFilePath | None = None,
        env: Mapping[str, str] | None = None,
    ) -> asyncio.coroutine:
        return self.async_call(
            *args, input=input, capture=capture, cwd=cwd, env=env
        )

    cls.__call__ = __call__  # type: ignore[assignment]
    return cls
```

**Usage:**

```python
@async_command
class MyCommand(Command):
    pass

async def main():
    cmd = MyCommand("ls")
    result = await cmd("-la")
```

**Trade-offs:**

- (+) Cleanest async design — true coroutine
- (+) No `asyncio.run()` overhead
- (+) Composable with other `await` expressions
- (-) Breaking API change — `cmd()` returns coroutine, not `str | bytes`
- (-) Dropped `text`/`encoding` params (caller must decode)
- (-) Can't be used from sync code

## Approach 3: Dual-Mode

Returns a coroutine if in an event loop, runs synchronously otherwise.
Most flexible but hardest to type.

```python
def async_command(cls: _C) -> _C:
    original_call = cls.__call__

    def __call__(
        self,
        *args: str,
        input: str | bytes | None = None,
        capture: bool = True,
        text: bool = True,
        encoding: str | None = "UTF-8",
        cwd: AnyFilePath | None = None,
        env: Mapping[str, str] | None = None,
    ) -> str | bytes | asyncio.coroutine:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        async_input = (
            input
            if isinstance(input, (bytes, type(None)))
            else input.encode(encoding or "UTF-8")
        )

        if loop is not None and loop.is_running():
            async def _call() -> str | bytes:
                result = await self.async_call(
                    *args, input=async_input, capture=capture, cwd=cwd, env=env
                )
                return result.decode(encoding or "UTF-8") if text else result
            return _call()

        result: bytes = asyncio.run(
            self.async_call(
                *args, input=async_input, capture=capture, cwd=cwd, env=env
            )
        )
        return result.decode(encoding or "UTF-8") if text else result

    cls.__call__ = __call__  # type: ignore[assignment]
    return cls
```

**Trade-offs:**

- (+) Works in both sync and async contexts transparently
- (+) Preserves `text`/`encoding` in sync mode
- (-) Return type is overloaded (`str | bytes | Coroutine`) — type checking nightmare
- (-) Caller must know whether to `await` or not
- (-) Most complex to maintain and document

## Recommendation

**Approach 1** is the best fit for `standard-deluxe`:

- Non-breaking — existing callers see the same API
- Preserves parameters — `text` and `encoding` continue to work
- Clear fallback — sync subprocess when inside an event loop
- Easy to reason about — the decorator is self-contained

`asyncio.run()` is the standard bridge between sync and async code, and
the fallback to sync `subprocess.run()` handles the edge case of being
called from within an already-running event loop.
