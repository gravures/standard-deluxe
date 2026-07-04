# Command Pipe Feature

## Overview

Adding bash-like pipe behavior to the `Command` class in `src/deluxe/process.py`.

**Goal**: Allow users to chain commands together where the stdout of one command becomes the stdin of the next, similar to bash pipes.

**Current State**: The `Command` class only supports executing single commands with optional input/output capture. There's no mechanism to connect multiple commands together.

---

## Current Architecture Analysis

The `Command` class has these limitations for piping:

- **No pipeline concept**: `__call__` executes a single command and returns its output
- **No stdout/stdin chaining**: Uses `subprocess.run` which captures all output at once
- **No operator overloading**: No way to use `|` syntax like in bash
- **Error handling is per-command**: Errors are raised immediately, but in a pipeline, we might want to handle errors differently

---

## Alternative Approaches

### Approach 1: `Pipeline` Class with `|` Operator Overloading (Recommended)

**Description**: Create a separate `Pipeline` class that manages a chain of commands, and add `__or__` to `Command` to enable `cmd1 | cmd2 | cmd3` syntax.

**Key Trade-offs**:
- Complexity: Medium - requires a new class and operator overloading
- Performance: Good - uses `subprocess.Popen` with direct pipe connections
- Maintainability: High - clean separation of concerns
- Flexibility: High - supports both sync and async execution

**Code Example**:

```python
class Pipeline:
    """A chain of commands connected by pipes.

    Represents a sequence of commands where each command's stdout
    is connected to the next command's stdin, similar to bash pipes.
    """

    def __init__(self, *commands: Command | str) -> None:
        self._commands = list(commands)

    def __or__(self, other: Command | str) -> Pipeline:
        """Add another command to the pipeline."""
        return Pipeline(*self._commands, other)

    def __call__(
        self,
        input: str | bytes | None = None,
        text: bool = True,
        encoding: str | None = "UTF-8",
        cwd: AnyFilePath | None = None,
        env: Mapping[str, str] | None = None,
    ) -> str | bytes:
        """Execute the pipeline synchronously."""
        if len(self._commands) == 0:
            return "" if text else b""

        processes = []
        try:
            # Start all processes except the last
            for i, cmd in enumerate(self._commands):
                if isinstance(cmd, str):
                    cmd = Command(cmd)

                is_last = i == len(self._commands) - 1
                stdin = subprocess.PIPE if i > 0 else (input if i == 0 else None)
                stdout = None if is_last else subprocess.PIPE

                proc = subprocess.Popen(
                    cmd._compose() if hasattr(cmd, '_compose') else (cmd,),
                    stdin=stdin,
                    stdout=stdout,
                    stderr=subprocess.PIPE if is_last else None,
                    text=text,
                    encoding=encoding if text else None,
                    cwd=cwd,
                    env=env,
                )
                processes.append(proc)

            # Feed input to first process if provided
            if input and processes:
                processes[0].stdin.write(input if isinstance(input, str) else input.decode())
                processes[0].stdin.close()

            # Wait for all processes
            for proc in processes[:-1]:
                proc.wait()

            # Get output from last process
            if processes:
                stdout, stderr = processes[-1].communicate()
                if processes[-1].returncode:
                    raise Command.Error(stderr, processes[-1].returncode)
                return stdout or ("" if text else b"")

            return "" if text else b""
        finally:
            # Cleanup any remaining processes
            for proc in processes:
                if proc.poll() is None:
                    proc.terminate()

# Add to Command class:
class Command:
    def __or__(self, other: Command | str) -> Pipeline:
        """Create a pipeline: cmd1 | cmd2."""
        return Pipeline(self, other)

    def pipe(self, *commands: Command | str) -> Pipeline:
        """Create a pipeline with multiple commands."""
        return Pipeline(self, *commands)
```

**Potential Issues**:
- Need to handle SIGPIPE errors when downstream commands exit early
- Resource cleanup if an error occurs mid-pipeline
- Complex error handling for which command failed

---

### Approach 2: Direct `pipe()` Method with Callbacks

**Description**: Add a `pipe()` method that takes a callback function to process output before passing it to the next command.

**Key Trade-offs**:
- Complexity: Low - simpler API
- Performance: Medium - buffering overhead
- Maintainability: High - easy to understand
- Flexibility: Medium - less flexible than full pipeline

**Code Example**:

```python
class Command:
    def pipe(
        self,
        *args: str,
        input: str | bytes | None = None,
        text: bool = True,
        encoding: str | None = "UTF-8",
        cwd: AnyFilePath | None = None,
        env: Mapping[str, str] | None = None,
    ) -> str | bytes:
        """Run command and return output (for manual chaining)."""
        return self.__call__(
            *args,
            input=input,
            text=text,
            encoding=encoding,
            cwd=cwd,
            env=env,
        )

# Usage: Manual chaining
result = cmd1("arg1") | cmd2("arg2") | cmd3("arg3")
# This is just: result = cmd3("arg3", input=cmd2("arg2", input=cmd1("arg1")))
```

**Potential Issues**:
- Each command waits for the previous to complete before starting
- No parallel execution of independent commands
- Memory usage for large outputs

---

### Approach 3: Shell-based Pipes (Not Recommended)

**Description**: Use `shell=True` with pipe syntax.

**Key Trade-offs**:
- Complexity: Very Low - simplest implementation
- Performance: Good - shell handles piping
- Maintainability: Low - breaks current design principle
- Security: Low - shell injection risks

**Code Example**:

```python
class Command:
    def shell_pipe(self, *args: str) -> str:
        """Execute using shell pipes (NOT RECOMMENDED)."""
        import shlex
        cmd_str = f"{self.command} {' '.join(shlex.quote(a) for a in args)}"
        cp = subprocess.run(cmd_str, shell=True, capture_output=True, text=True)
        if cp.returncode:
            raise Command.Error(cp.stderr, cp.returncode)
        return cp.stdout
```

**Potential Issues**:
- Shell injection vulnerabilities
- Breaks the "commands are never executed through a shell" principle
- Platform-specific behavior

---

## Recommended Implementation

**Approach 1** with these enhancements:

1. **Add `Pipeline` class** in `process.py`
2. **Add `__or__` operator** to `Command`
3. **Add `pipe()` method** for explicit pipeline creation
4. **Support both sync and async** execution
5. **Proper error handling** with `Pipeline.Error`

**Key Design Decisions**:
- Use `subprocess.Popen` for direct pipe connections (not shell)
- Support both text and binary modes
- Allow partial pipeline execution (stop at first error or continue)
- Clean up resources properly on failure

---

## Next Steps

1. **Create `Pipeline` class** with basic sync execution (2-3 hours)
2. **Add `__or__` operator** to `Command` (30 minutes)
3. **Implement async pipeline** with `asyncio.subprocess` (2-3 hours)
4. **Add error handling** and cleanup (1-2 hours)
5. **Write tests** for various scenarios (2-3 hours)
6. **Update documentation** (1 hour)

**Total estimated time**: 8-12 hours

---

## Test Cases

```python
# tests/test_pipeline.py

def test_simple_pipe():
    """Test basic pipe: echo 'hello' | cat"""
    echo = Command("echo")
    cat = Command("cat")
    pipeline = echo | cat
    result = pipeline(input="hello\n")
    assert result.strip() == "hello"

def test_multiple_pipes():
    """Test: echo 'hello' | cat | cat"""
    echo = Command("echo")
    cat = Command("cat")
    pipeline = echo("hello") | cat | cat
    result = pipeline()
    assert result.strip() == "hello"

def test_pipe_with_args():
    """Test: ls -la | grep '.py'"""
    ls = Command("ls")
    grep = Command("grep")
    pipeline = ls("-la") | grep(".py")
    result = pipeline()
    assert ".py" in result

def test_pipeline_error_handling():
    """Test error in pipeline raises appropriate error"""
    false = Command("false")
    cat = Command("cat")
    pipeline = false | cat
    with pytest.raises(Pipeline.Error):
        pipeline()
```
