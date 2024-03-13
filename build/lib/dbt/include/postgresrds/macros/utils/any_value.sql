{#- /*postgresrds doesn't support any_value, so we're using min() to get the same result*/ -#}

{% macro postgresrds__any_value(expression) -%}

    min({{ expression }})

{%- endmacro %}
