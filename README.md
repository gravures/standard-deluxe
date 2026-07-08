# Standard-Deluxe

<!-- rst content start -->

[![pdm-managed](https://img.shields.io/badge/pdm-managed-blueviolet)](https://pdm-project.org) ![Python Version from PEP 621 TOML](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fgravures%2Fstandard-deluxe%2Fmain%2Fpyproject.toml) ![Tests](https://github.com/gravures/standard-deluxe/actions/workflows/main.yml/badge.svg) ![coverage badge](assets/coverage.svg) ![GitHub License](https://img.shields.io/github/license/gravures/standard-deluxe) ![OS support](https://img.shields.io/badge/OS-macOS%20Linux%20Windows-red) <!-- rumdl-disable-line MD013 -->


---

**Standard-Deluxe** is an open-Source _general-purpose_ Python library.

## Overview

**Standard-Deluxe** provides a handpicked collection of enhanced Python modules
that extend the standard library with robust, type-safe, and `pythonic` solutions.
Standard-Deluxe is positioned as a general Python library tailored for application
development.

The name **Standard-Deluxe** draws inspiration from the argentic photography era's
_Agfa Standard Deluxe_ cameras known for their high quality and craftsmanship.


## Getting Started

### Requirements

- Python 3.11 or higher
- No external dependencies required

### Installation

Add library to your `pyproject.toml` dependencies:

```toml
[project]
dependencies = [ "standard-deluxe" ]
```

Using `uv` to add library to your `pyproject.toml`:

```sh
uv add standard-deluxe
```

Or to install in a dedicated virtual environment.

```sh
uv pip install standard-deluxe
```

Alternatively, you can install it with pip:

```sh
pip install standard-deluxe
```

## Usage

Standard-Deluxe modules are designed to integrate seamlessly with your existing
Python workflows, providing enhanced functionality. The python library name is
just `deluxe`:

```python
from deluxe.types import Unset

my_var: str = Unset
```

**Type Safety First**: Type safety is a foundational concern. Constant effort is
dedicated to make accurate and meaningful type annotations that work seamlessly
with static type checkers like pyright/basedpyright, or mypy.

**Comprehensive Documentation**: Every API is documented with well-formatted
docstrings used to generate API HTML documentation and offer useful hints
inside `IDE` or with python help() function call.

**Zero Dependencies**: Built with no external dependencies as pure Python
or c based extension module where performance is a concern.

**Pythonic**: Adherence to Python best practices with careful avoidance
of anti-patterns, following the principle that code should be both elegant and practical.

**PEP 8 Compliance**: All APIs follow Python naming conventions and style guidelines
for consistent, readable code.

<!-- rst content end -->

## Contributing

Contributors are always welcome. Feel free to grab an [issue](https://github.com/gravures/standard-deluxe/issues) to work on or make a suggested improvement. If you wish to contribute, please read the [Contribution Guide](https://github.com/gravures/standard-deluxe/contributing.md) and [Code of Conduct](https://github.com/gravures/standard-deluxe/code_of_conduct.md). <!-- rumdl-disable-line MD013 -->

## Similar Projects

[python-boltons](https://github.com/orgs/python-boltons/repositories): share the spirit of extending Python's standard library with useful additions.

## Acknowledgments

coming soon...

## License

Use of this repository is authorized under the [GPL-3.0](https://github.com/gravures/standard-deluxe/LICENSE).
