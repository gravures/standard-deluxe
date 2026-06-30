{% macro _render_item_name(obj, sig=False, role='py:obj') -%}
:{{ role }}:`{{ obj.name }} <{{ obj.id }}>`
    {%- if sig -%}
        \ (
        {%- for arg in obj.obj.args -%}
            {%- if arg[0] %}{{ arg[0]|replace('*', '\*') }}{% endif -%}{{  arg[1] -}}
            {%- if not loop.last  %}, {% endif -%}
        {%- endfor -%}
        ){%- endif -%}
{%- endmacro %}

{% macro _item(obj, sig=False, label='', role='py:obj') %}
    * - {% if label %}:obj:`{{ label }}` {% endif %}{{ _render_item_name(obj, sig, role) }}
      - {% if obj.summary %}{{ obj.summary|truncate(50, False, '...', 0) }}{% else %}\-{% endif +%}
{% endmacro %}

{% macro auto_summary(objs, title='') -%}
.. list-table:: {{ title }}
    :header-rows: 0
    :width: 100%
    :align: left
    :class: summarytable

    {% for obj in objs -%}
        {%- set sig = (obj.type in ['method', 'function'] and not 'property' in obj.properties) -%}

        {%- if obj.type == 'class' -%}
        {%- set role = 'class' -%}
        {%- elif obj.type == 'method' -%}
        {%- set role = 'meth' -%}
        {%- elif obj.type == 'function' -%}
        {%- set role = 'func' -%}
        {%- elif obj.type == 'attribute' -%}
        {%- set role = 'attr' -%}
        {%- else -%}
        {%- set role = 'obj' -%}
        {%- endif -%}

        {%- if 'property' in obj.properties -%}
        {%- set label = 'property' -%}
        {%- elif 'classmethod' in obj.properties -%}
        {%- set label = 'classmethod' -%}
        {%- elif 'abstractmethod' in obj.properties -%}
        {%- set label = 'abc' -%}
        {%- elif 'staticmethod' in obj.properties -%}
        {%- set label = 'staticmethod' -%}
        {%- else -%}
        {%- set label = '' -%}
        {%- endif -%}

        {{- _item(obj, sig=sig, label=label, role=role) -}}
    {%- endfor -%}

{% endmacro %}
