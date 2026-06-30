{% import 'macros.rst' as macros %}
{% if obj.display %}
.. py:{{ obj.type }}:: {{ obj.short_name }}{% if obj.args %}({{ obj.args }}){% endif %}

{% for (args, return_annotation) in obj.overloads %}
      {{ " " * (obj.type | length) }}   {{ obj.short_name }}{% if args %}({{ args }}){% endif %}

{% endfor %}

   {# EXTENDS #}
   {% if obj.bases %}
   {% if "show-inheritance" in autoapi_options %}
   Extends: {% for base in obj.bases %}{{ base|link_objs }}{% if not loop.last %}, {% endif %}{% endfor %}
   {% endif %}

   {# DIAGRAM #}
   {% if "show-inheritance-diagram" in autoapi_options and obj.bases != ["object"] %}
   .. autoapi-inheritance-diagram:: {{ obj.obj["full_name"] }}
      :parts: 1
      {% if "private-members" in autoapi_options %}
      :private-bases:
      {% endif %}

   {% endif %}

   {# DOCSTRING #}
   {% endif %}
   {% if obj.docstring %}
   {{ obj.docstring|indent(3) }}
   {% endif %}

   {# CLASS SUMMARY #}
   {% block summary scoped %}
   {% if "inherited-members" in autoapi_options %}
   {% set attrs = obj.attributes|selectattr("inherited")|selectattr("display")|list %}
   {% set cls = obj.classes|selectattr("inherited")|selectattr("display")|list %}
   {% set props = obj.properties|selectattr("inherited")|selectattr("display")|list %}
   {% set meths = obj.methods|selectattr("inherited")|selectattr("display")|list %}
   {% set inherited_members = attrs + cls + props + meths %}

   {% if inherited_members %}
   {{ macros.auto_summary(inherited_members, title="inherited Members") }}
   {% endif %}
   {% endif %}
   {% endblock %}

   {# CLASSES #}
   {% set visible_classes = obj.classes|rejectattr("inherited")|selectattr("display")|list %}
   {% for klass in visible_classes %}
   {{ klass.render()|indent(3) }}
   {% endfor %}

   {# PROPERTIES #}
   {% set visible_properties = obj.properties|rejectattr("inherited")|selectattr("display")|list %}
   {% for property in visible_properties %}
   {{ property.render()|indent(3) }}
   {% endfor %}

   {# ATTRIBUTES #}
   {% set visible_attributes = obj.attributes|rejectattr("inherited")|selectattr("display")|list %}
   {% for attribute in visible_attributes %}
   {{ attribute.render()|indent(3) }}
   {% endfor %}

   {# METHODS #}
   {% set visible_methods = obj.methods|rejectattr("inherited")|selectattr("display")|list %}
   {% for method in visible_methods %}
   {{ method.render()|indent(3) }}
   {% endfor %}
{% endif %}
