{% import 'macros.rst' as macros %}
{% if not obj.display %}
:orphan:

{% endif %}
{# THE HEADER PART FOR MODULE #}
:py:mod:`{{ obj.type + " " + obj.name }}`

{% if obj.summary %}
{{ obj.summary }}
{{ "==" * obj.summary|length }}

{% else %}
{{ obj.short_name|capitalize() }} {{ obj.type }}
{{ "==" * obj.name|length }}

{% endif %}

{% if obj.docstring %}
.. autoapi-nested-parse::
   {# Here we strip the summary line of the module previously printed #}
   {{ obj.docstring|indent(3)|replace(obj.summary, "", 1) }}

{% endif %}
{# END OF THE HEADER PART #}

{# TOCTREE #}
{% block subpackages %}
{% set visible_subpackages = obj.subpackages|selectattr("display")|list %}
{% if visible_subpackages %}
Subpackages
-----------
.. toctree::
   :titlesonly:
   :maxdepth: 3

{% for subpackage in visible_subpackages %}
   {# For toctree use the package short name instead #}
   {# of printing the full docstring title (the summary line) #}
   {{ subpackage.short_name }} package <{{ subpackage.short_name }}/index.rst>
{% endfor %}


{% endif %}
{% endblock %}
{% block submodules %}
{% set visible_submodules = obj.submodules|selectattr("display")|list %}
{% if visible_submodules %}
Submodules
----------
.. toctree::
   :titlesonly:
   :maxdepth: 1

{% for submodule in visible_submodules %}
   {# For toctree use the module short name instead #}
   {# of printing the full docstring title (the summary line) #}
   {{ submodule.short_name }} module <{{ submodule.short_name }}/index.rst>
{% endfor %}


{% endif %}
{% endblock %}
{% block content %}
{% if obj.all is not none %}
{% set visible_children = obj.children|selectattr("short_name", "in", obj.all)|list %}
{% elif obj.type is equalto("package") %}
{% set visible_children = obj.children|selectattr("display")|list %}
{% else %}
{% set visible_children = obj.children|selectattr("display")|rejectattr("imported")|list %}
{% endif %}
{% if visible_children %}
{{ obj.type|title }} Contents
{{ "-" * obj.type|length }}---------

{# SUMMARY #}
{% set visible_classes = visible_children|selectattr("type", "equalto", "class")|list %}
{% set visible_functions = visible_children|selectattr("type", "equalto", "function")|list %}
{% set visible_attributes = visible_children|selectattr("type", "equalto", "data")|list %}
{% if "show-module-summary" in autoapi_options and (visible_classes or visible_functions) %}
{% block classes scoped %}
{% if visible_classes %}

{{ macros.auto_summary(visible_classes, title="Classes") }}

{% endif %}
{% endblock %}

{% block functions scoped %}
{% if visible_functions %}

{{ macros.auto_summary(visible_functions, title="Functions") }}

{% endif %}
{% endblock %}

{% block attributes scoped %}
{% if visible_attributes %}

{{ macros.auto_summary(visible_attributes, title="Attributes") }}


{% endif %}
{% endblock %}
{% endif %}
{% for obj_item in visible_children %}
{{ obj_item.render()|indent(0) }}
{% endfor %}
{% endif %}
{% endblock %}
