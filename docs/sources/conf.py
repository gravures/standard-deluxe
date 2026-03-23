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
version = "unknown"
with (
    contextlib.suppress(OSError),
    Path(f"../../src/{project_lib}/_version.py").open("r", encoding="utf-8") as f,
):
    # we can't read dynamic variable from pyproject.toml
    line = None
    while line:
        line = f.readline()
        if line.startswith("__version__"):
            version = line.split()[-1]
            break
release = version.strip("'")

# SPHINX GLOBALS
extensions = [
    "autoapi.extension",
    "sphinx.ext.inheritance_diagram",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
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
autoapi_ignore = []
autoapi_root = "autoapi"
autoapi_type = "python"
autoapi_keep_files = False
autoapi_add_toctree_entry = False
autoapi_python_class_content = "both"
autoapi_member_order = "bysource"
autoapi_python_use_implicit_namespaces = True
autoapi_file_patterns = ["*.py", "*.pyi", "*.pyx"]
autoapi_template_dir = "sources/_templates/autoapi"
autodoc_typehints = "signature"
autodoc_inherit_docstrings = False
autoapi_options = [
    "members",
    "inherited-members",
    "undoc-members",
    # "private-members",
    "show-inheritance",
    "show-module-summary",
    # "special-members",
    # "imported-members",
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
templates_path = ["_templates"]
html_static_path = ["_static"]
html_theme = "furo"
# html_title = f"{project.capitalize()} {release}"
html_theme_options = {
    "sidebar_hide_name": True,
    "announcement": (
        f"<bold>{project.capitalize()}</bold> documentation<small>- version {release}</small>"
    ),
    "navigation_with_keys": True,
    "top_of_page_button": "edit",  # None
    "dark_logo": "logo_dark.png",
    "light_logo": "logo_light.png",
    "footer_icons": [
        {
            "name": "GitHub",
            "url": read_toml("project", "urls", "homepage"),
            "html": """
                <svg stroke="currentColor" fill="currentColor" stroke-width="0" viewBox="0 0 16 16">
                    <path fill-rule="evenodd" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z"></path>
                </svg>
            """,
            "class": "",
        },
    ],
}


# MAN PAGES
# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [("index", f"{project}.tex", f"{project} Documentation", [f"{author}"], 1)]
# man_show_urls = False
