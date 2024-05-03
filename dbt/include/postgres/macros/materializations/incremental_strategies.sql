{% macro postgres__get_incremental_merge_sql(arg_dict) %}
  {{ create_incremental_missing_partitions(arg_dict) }}

  {% do return(default__get_incremental_merge_sql(arg_dict)) %}  
{% endmacro %}

{% macro postgres__get_incremental_delete_insert_sql(arg_dict) %}
  {{ create_incremental_missing_partitions(arg_dict) }}

  {% do return(default__get_incremental_delete_insert_sql(arg_dict)) %}
{% endmacro %}

{% macro postgres__get_incremental_append_sql(arg_dict) %}
  {{ create_incremental_missing_partitions(arg_dict) }}

  {% do return(default__get_incremental_append_sql(arg_dict)) %}
{% endmacro %}

{% macro create_incremental_missing_partitions(arg_dict) %}
  {%- set target = arg_dict["target_relation"] -%}
  {%- set source = arg_dict["temp_relation"] -%}
  {%- set unlogged = config.get('unlogged') %}

  {#
    -- New data might get inserted to a partition that still does not exist
    -- We need to perform an anti join between the partitions that exist in the new (source) table and the target table
    -- Partitions that don't exist will be created
  #}
  {%- set missing_partitions_query %}
  with
    new_partitions as (
      -- Get the partitions present on the new, temporary source table
      select
        inhrelid::regclass as from_table_name,
        regexp_substr(inhrelid::regclass::text, '[^_]*$') as partition_suffix, -- Get the string after the last underscore
        pg_get_expr(c.relpartbound, c.oid, true) as partition_expression
      from pg_inherits i
      join pg_class c_parent on i.inhparent = c_parent.oid
      join pg_class c on i.inhrelid = c.oid
      where c.relnamespace = pg_my_temp_schema()::regclass
        and c_parent.relname = '{{ source.identifier }}'
    ),
    existing_partitions as (
      -- Partitions already available on the target table
      select
        pg_get_expr(c.relpartbound, c.oid, true) as partition_expression
      from pg_inherits i
      join pg_class c_parent on i.inhparent = c_parent.oid
      join pg_class c on i.inhrelid = c.oid
      join pg_namespace ns on c.relnamespace = ns.oid
      where ns.nspname = '{{ target.schema }}' and c_parent.relname = '{{ target.identifier }}'
    ),
    missing_partitions as (
      -- Find the partitions that exist on the source table but not on the target
      select
        np.from_table_name,
        partition_suffix,
        partition_expression
      from new_partitions np
      left join existing_partitions ep using (partition_expression)
      where ep.partition_expression is null
    )
    select *
    from missing_partitions
  {% endset %}

  {% set missing_partitions = run_query(missing_partitions_query) %}
  {% for missing_partition in missing_partitions.rows %}
    {%- set partition_relation = make_intermediate_relation(target, missing_partition['partition_suffix']) %}

    -- Create the missing partition
    create {% if unlogged -%}
        unlogged
      {%- endif %} 
      table
    "{{ target.schema }}"."{{ partition_relation.identifier }}"
    partition of {{ target }} {{ missing_partition.partition_expression }};
  {% endfor %}

  {# Ensure a statement is executed even if no new partitions were created #}
  select 1;

{% endmacro %}