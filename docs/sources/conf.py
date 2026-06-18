# ruff: noqa: CPY001, INP001, DOC201, DOC501, E501
"""Configuration file for the Sphinx documentation builder.

https://www.sphinx-doc.org/en/master/usage/configuration.html
https://bylr.info/articles/2022/05/10/api-doc-with-sphinx-autoapi/
"""

from __future__ import annotations

import contextlib
import sys
import tomllib
from pathlib import Path


# PATH SETUP
# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, str(Path("../../src").resolve()))


def read_toml(*args: str):
    """Looks for property in pyproject.toml."""
    entry = None
    try:
        with (Path(__file__).parent.parent.parent / "pyproject.toml").open(
            "r", encoding="utf-8"
        ) as stream:
            section = tomllib.loads(stream.read())
            for entry in args[:-1]:
                section = section[entry]
    except LookupError as err:
        msg = f"pyproject.toml does not contain a <{entry}> section."
        raise LookupError(msg) from err
    else:
        try:
            result = section[args[-1]]
        except LookupError as err:
            msg = f"{entry} section does not contain a <{args[-1]}> property."
            raise LookupError(msg) from err
    return result


# GENERAL CONFIGURATION
project: str = read_toml("project", "name")
project_lib = "deluxe"
authors = [a["name"] for a in read_toml("project", "authors")]
author = ", ".join(authors)
documentation_summary = read_toml("project", "description")

# VERSIONS HANDLING
version = None
with (
    contextlib.suppress(OSError),
    (Path(__file__).parent.parent.parent / f"src/{project_lib}/_version.py").open(
        "r", encoding="utf-8"
    ) as file_,
):
    # we can't read dynamic variable from pyproject.toml
    _, _, version = file_.readline().partition("=")
version = version or "unknown"
release = version.strip(" '")

# SPHINX GLOBALS
extensions = [
    "autoapi.extension",
    "sphinx.ext.inheritance_diagram",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
    "sphinx_immaterial",
    "myst_parser",
]
exclude_patterns = ["build", "Thumbs.db", ".DS_Store"]
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}
maximum_signature_line_length = 120
add_function_parentheses = True
add_module_names = False
modindex_common_prefix = [f"{project_lib}."]

# SPHINX AUTO-API
autoapi_dirs = [f"../../src/{project_lib}"]
autoapi_ignore = []  # ["**/_types.pyx"]
autoapi_root = "autoapi"
autoapi_type = "python"
autoapi_keep_files = False
autoapi_add_toctree_entry = False
autoapi_python_class_content = "both"
autoapi_member_order = "bysource"
autoapi_python_use_implicit_namespaces = True
autoapi_file_patterns = ["*.py", "*.pyi"]
autoapi_template_dir = "sources/_templates/autoapi"
autodoc_typehints = "signature"
autodoc_inherit_docstrings = False
autoapi_options = [
    "members",
    "inherited-members",
    "undoc-members",
    "show-inheritance",
    "show-module-summary",
    "imported-members",
    # "private-members",
    # "special-members",
    # "show-inheritance-diagram"
]


# NAPOLEON
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = False
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_keyword = False
napoleon_use_rtype = False
napoleon_preprocess_types = False
napoleon_type_aliases = True
napoleon_attr_annotations = False
napoleon_custom_sections = [
    ("Classes", "params_style"),
    ("Functions", "params_style"),
    ("Variables", "params_style"),
    ("Constants", "params_style"),
    ("Enums", "params_style"),
]

# INHERITANCE DIAGRAM
inheritance_graph_attrs = {
    "rankdir": "LR",
    "fontsize": 12,
    "ratio": "auto",
    "pad": 0.2,
    "fontcolor": "blue",
}
inheritance_node_attrs = {
    "shape": "box3d",
    "ratio": "compress",
    "fontsize": 12,
    "height": 1.2,
    "fontcolor": "black",
    "color": "wite",
    "style": "filled",
    "fillcolor": "chocolate",
}
inheritance_edge_attrs = {
    "color": "brown",
    "arrowsize": 1.2,
    "penwidth": 2,
    "style": "bold",
}

# HTML OUTPUT
# see: https://jbms.github.io/sphinx-immaterial/customization.html#customization
templates_path = ["_templates"]
html_static_path = ["_static"]
html_theme = "sphinx_immaterial"
html_logo = None
html_theme_options = {
    "icon": {"logo": "material/library"},
    "repo_url": read_toml("project", "urls", "repository"),
    "features": [
        "header.autohide",
        "navigation.footer",
        # "navigation.instant",  # BUG: break content.code.copy !
        "navigation.sections",
        "navigation.top",
        "navigation.tracking",
        "content.code.copy",
        "content.tooltips",
        "search.highlight",
        "search.share",
        # "toc.sticky",
    ],
    "toc_title_is_page_title": True,
    "font": {
        "text": "Roboto",  # used for all the pages' text
        "code": "Roboto Mono",  # used for literal code blocks
    },
    "palette": [
        {
            "media": "(prefers-color-scheme)",
            "scheme": "default",
            "primary": "deep-purple",
            "accent": "lime",
            "toggle": {
                "icon": "material/lightbulb",
                "name": "Switch to light mode",
            },
        },
        {
            "media": "(prefers-color-scheme: light)",
            "scheme": "default",
            "primary": "purple",
            "accent": "teal",
            "toggle": {
                "icon": "material/lightbulb",
                "name": "Switch to dark mode",
            },
        },
        {
            "media": "(prefers-color-scheme: dark)",
            "scheme": "slate",
            "primary": "deep-purple",
            "accent": "lime",
            "toggle": {
                "icon": "material/lightbulb",
                "name": "Switch to system preference",
            },
        },
    ],
    "status": {
        "new": {"title": "Recently added", "icon": "material/alert-decagram"},
        "deprecated": {"title": "Deprecated", "icon": "material/trash-can"},
    },
    "navigation_with_keys": True,
}


# MAN PAGES
# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [("index", f"{project}.tex", f"{project} Documentation", [f"{author}"], 1)]
# man_show_urls = False
