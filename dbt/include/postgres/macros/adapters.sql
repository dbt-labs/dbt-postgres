{% macro postgres__create_table_as(temporary, relation, sql) -%}
  {%- set unlogged = config.get('unlogged', default=false) -%}
  {%- set sql_header = config.get('sql_header', none) -%}

  {{ sql_header if sql_header is not none }}

  {% if config.get('partition_by') != None %}
    {# Use partitioning #}

    {%- set partition_by_field = config.get('partition_by')['field'] -%}
    {%- set partition_by_granularity = config.get('partition_by')['granularity'] -%}

    -- We cannot create a partitioned table with "create as select".
    -- Create a dummy temporary table just to be used as a template for the real one
    create temporary table "{{ this.identifier }}__tt" as
    select *
    from ({{ sql }}) model_subq
    where 1 = 2;

    -- Create partitioned table as a copy of the template
    create {% if temporary -%}
        temporary
      {%- elif unlogged -%}
        unlogged
      {%- endif %} table {{ relation }} (like "{{ this.identifier }}__tt")
      partition by range ({{ partition_by_field }});

    {% set required_partitions_query %}
      -- Partitions need to be manually created before inserting.
      -- We execute the model SQL to get the first and last partitions and use the granularity to define what others need to be created.
      -- 
      -- Note that we this executes the SQL model a first time just to get the partitions and it will be done a second time to actually get the data.
      -- That might be very inefficient depending on the selected volume of data.
      -- There's a alternative:
      -- - Create as select a temporary non-partitioned table.
      -- - Get the min/max partitions from that table.
      -- - Move the data to the final table once it's partitioned.
      --
      -- That option would mean the data is stored twice during model execution.
      with partitions as (
          -- Generate a sequence with one row per required partition, based on the min and max dates
          select
              generate_series(
                  date_trunc('{{ partition_by_granularity }}', min({{ partition_by_field }})),
                  date_trunc('{{ partition_by_granularity }}', max({{ partition_by_field }})),
                  '1 {{ partition_by_granularity }}'::interval
              ) as begin_date
          from (
            {{ sql }}
          ) model_subq
      )
      select
          -- Generate the begin-end date and name suffix for each partition
          begin_date,
          begin_date + '1 {{ partition_by_granularity }}'::interval as end_date,
          to_char(begin_date, '_yyyymmdd') as partition_suffix
      from partitions;
    {% endset %}
    {% set required_partitions_results = run_query(required_partitions_query) %}

    -- Create the required partitions
    {% for required_partition in required_partitions_results.rows %}
      create
      {% if temporary -%}
        temporary
      {%- elif unlogged -%}
        unlogged
      {%- endif %}
      table
      {{ make_intermediate_relation(relation, required_partition['partition_suffix']) }}
      partition of {{ relation }} for values from ('{{ required_partition["begin_date"] }}'::timestamp) to ('{{ required_partition["end_date"] }}'::timestamp);
    {% endfor %}

    -- Insert into the parent table
    insert into {{ relation }}
    {{ sql }};
  {% else %}
     create {% if temporary -%}
        temporary
      {%- elif unlogged -%}
        unlogged
      {%- endif %} table {{ relation }}
      {% set contract_config = config.get('contract') %}
      {% if contract_config.enforced %}
        {{ get_assert_columns_equivalent(sql) }}
      {% endif -%}
      {% if contract_config.enforced and (not temporary) -%}
          {{ get_table_columns_and_constraints() }} ;
        insert into {{ relation }} (
          {{ adapter.dispatch('get_column_names', 'dbt')() }}
        )
        {%- set sql = get_select_subquery(sql) %}
      {% else %}
        as
      {% endif %}
      (
        {{ sql }}
      );
  {% endif %}
{%- endmacro %}

{% macro postgres__rename_relation(from_relation, to_relation) %}
  {% set target_name = adapter.quote_as_configured(to_relation.identifier, 'identifier') %}
  {% call statement('rename_relation') -%}
    alter table {{ from_relation }} rename to {{ target_name }};

    {# If the relation is partitioned, rename the subtables #}
    {% set existing_partitions_query %}
      select
        inhrelid::regclass as from_table_name,
        regexp_substr(inhrelid::regclass::text, '[^_]*$') as partition_suffix -- Get the string after the last underscore
      from pg_inherits i
      join pg_class c on i.inhparent = c.oid
      join pg_namespace ns on c.relnamespace = ns.oid
      where ns.nspname = '{{ from_relation.schema }}' and c.relname = '{{ from_relation.identifier }}';
    {% endset %}
    {% set existing_partitions_results = run_query(existing_partitions_query) %}

    -- Rename the existing partitions
    {% for existing_partition in existing_partitions_results.rows %}
      {%- set partition_relation = make_intermediate_relation(to_relation, existing_partition['partition_suffix']) %}

      alter table {{ existing_partition["from_table_name"] }} rename to {{ partition_relation.identifier }};
    {% endfor %}
  {%- endcall %}
{% endmacro %}

{% macro postgres__get_create_index_sql(relation, index_dict) -%}
  {%- set index_config = adapter.parse_index(index_dict) -%}
  {%- set comma_separated_columns = ", ".join(index_config.columns) -%}
  {%- set index_name = index_config.render(relation) -%}

  create {% if index_config.unique -%}
    unique
  {%- endif %} index if not exists
  "{{ index_name }}"
  on {{ relation }} {% if index_config.type -%}
    using {{ index_config.type }}
  {%- endif %}
  ({{ comma_separated_columns }})
{%- endmacro %}

{% macro postgres__create_schema(relation) -%}
  {% if relation.database -%}
    {{ adapter.verify_database(relation.database) }}
  {%- endif -%}
  {%- call statement('create_schema') -%}
    create schema if not exists {{ relation.without_identifier().include(database=False) }}
  {%- endcall -%}
{% endmacro %}

{% macro postgres__drop_schema(relation) -%}
  {% if relation.database -%}
    {{ adapter.verify_database(relation.database) }}
  {%- endif -%}
  {%- call statement('drop_schema') -%}
    drop schema if exists {{ relation.without_identifier().include(database=False) }} cascade
  {%- endcall -%}
{% endmacro %}

{% macro postgres__get_columns_in_relation(relation) -%}
  {% call statement('get_columns_in_relation', fetch_result=True) %}
      select
          column_name,
          data_type,
          character_maximum_length,
          numeric_precision,
          numeric_scale

      from {{ relation.information_schema('columns') }}
      where table_name = '{{ relation.identifier }}'
        {% if relation.schema %}
        and table_schema = '{{ relation.schema }}'
        {% endif %}
      order by ordinal_position

  {% endcall %}
  {% set table = load_result('get_columns_in_relation').table %}
  {{ return(sql_convert_columns_in_relation(table)) }}
{% endmacro %}


{% macro postgres__list_relations_without_caching(schema_relation) %}
  {% call statement('list_relations_without_caching', fetch_result=True) -%}
    select
      '{{ schema_relation.database }}' as database,
      tablename as name,
      schemaname as schema,
      'table' as type
    from pg_tables
    where schemaname ilike '{{ schema_relation.schema }}'
    union all
    select
      '{{ schema_relation.database }}' as database,
      viewname as name,
      schemaname as schema,
      'view' as type
    from pg_views
    where schemaname ilike '{{ schema_relation.schema }}'
    union all
    select
      '{{ schema_relation.database }}' as database,
      matviewname as name,
      schemaname as schema,
      'materialized_view' as type
    from pg_matviews
    where schemaname ilike '{{ schema_relation.schema }}'
  {% endcall %}
  {{ return(load_result('list_relations_without_caching').table) }}
{% endmacro %}

{% macro postgres__information_schema_name(database) -%}
  {% if database_name -%}
    {{ adapter.verify_database(database_name) }}
  {%- endif -%}
  information_schema
{%- endmacro %}

{% macro postgres__list_schemas(database) %}
  {% if database -%}
    {{ adapter.verify_database(database) }}
  {%- endif -%}
  {% call statement('list_schemas', fetch_result=True, auto_begin=False) %}
    select distinct nspname from pg_namespace
  {% endcall %}
  {{ return(load_result('list_schemas').table) }}
{% endmacro %}

{% macro postgres__check_schema_exists(information_schema, schema) -%}
  {% if information_schema.database -%}
    {{ adapter.verify_database(information_schema.database) }}
  {%- endif -%}
  {% call statement('check_schema_exists', fetch_result=True, auto_begin=False) %}
    select count(*) from pg_namespace where nspname = '{{ schema }}'
  {% endcall %}
  {{ return(load_result('check_schema_exists').table) }}
{% endmacro %}

{#
  Postgres tables have a maximum length of 63 characters, anything longer is silently truncated.
  Temp and backup relations add a lot of extra characters to the end of table names to ensure uniqueness.
  To prevent this going over the character limit, the base_relation name is truncated to ensure
  that name + suffix + uniquestring is < 63 characters.
#}

{% macro postgres__make_relation_with_suffix(base_relation, suffix, dstring) %}
    {% if dstring %}
      {% set dt = modules.datetime.datetime.now() %}
      {% set dtstring = dt.strftime("%H%M%S%f") %}
      {% set suffix = suffix ~ dtstring %}
    {% endif %}
    {% set suffix_length = suffix|length %}
    {% set relation_max_name_length = base_relation.relation_max_name_length() %}
    {% if suffix_length > relation_max_name_length %}
        {% do exceptions.raise_compiler_error('Relation suffix is too long (' ~ suffix_length ~ ' characters). Maximum length is ' ~ relation_max_name_length ~ ' characters.') %}
    {% endif %}
    {% set identifier = base_relation.identifier[:relation_max_name_length - suffix_length] ~ suffix %}

    {{ return(base_relation.incorporate(path={"identifier": identifier })) }}

  {% endmacro %}

{% macro postgres__make_intermediate_relation(base_relation, suffix) %}
    {{ return(postgres__make_relation_with_suffix(base_relation, suffix, dstring=False)) }}
{% endmacro %}

{% macro postgres__make_temp_relation(base_relation, suffix) %}
    {% set temp_relation = postgres__make_relation_with_suffix(base_relation, suffix, dstring=True) %}
    {{ return(temp_relation.incorporate(path={"schema": none,
                                              "database": none})) }}
{% endmacro %}

{% macro postgres__make_backup_relation(base_relation, backup_relation_type, suffix) %}
    {% set backup_relation = postgres__make_relation_with_suffix(base_relation, suffix, dstring=False) %}
    {{ return(backup_relation.incorporate(type=backup_relation_type)) }}
{% endmacro %}

{#
  By using dollar-quoting like this, users can embed anything they want into their comments
  (including nested dollar-quoting), as long as they do not use this exact dollar-quoting
  label. It would be nice to just pick a new one but eventually you do have to give up.
#}
{% macro postgres_escape_comment(comment) -%}
  {% if comment is not string %}
    {% do exceptions.raise_compiler_error('cannot escape a non-string: ' ~ comment) %}
  {% endif %}
  {%- set magic = '$dbt_comment_literal_block$' -%}
  {%- if magic in comment -%}
    {%- do exceptions.raise_compiler_error('The string ' ~ magic ~ ' is not allowed in comments.') -%}
  {%- endif -%}
  {{ magic }}{{ comment }}{{ magic }}
{%- endmacro %}


{% macro postgres__alter_relation_comment(relation, comment) %}
  {% set escaped_comment = postgres_escape_comment(comment) %}
  comment on {{ relation.type }} {{ relation }} is {{ escaped_comment }};
{% endmacro %}


{% macro postgres__alter_column_comment(relation, column_dict) %}
  {% set existing_columns = adapter.get_columns_in_relation(relation) | map(attribute="name") | list %}
  {% for column_name in column_dict if (column_name in existing_columns) %}
    {% set comment = column_dict[column_name]['description'] %}
    {% set escaped_comment = postgres_escape_comment(comment) %}
    comment on column {{ relation }}.{{ adapter.quote(column_name) if column_dict[column_name]['quote'] else column_name }} is {{ escaped_comment }};
  {% endfor %}
{% endmacro %}

{%- macro postgres__get_show_grant_sql(relation) -%}
  select grantee, privilege_type
  from {{ relation.information_schema('role_table_grants') }}
      where grantor = current_role
        and grantee != current_role
        and table_schema = '{{ relation.schema }}'
        and table_name = '{{ relation.identifier }}'
{%- endmacro -%}

{% macro postgres__copy_grants() %}
    {{ return(False) }}
{% endmacro %}


{% macro postgres__get_show_indexes_sql(relation) %}
    select
        i.relname                                   as name,
        m.amname                                    as method,
        ix.indisunique                              as "unique",
        array_to_string(array_agg(a.attname), ',')  as column_names
    from pg_index ix
    join pg_class i
        on i.oid = ix.indexrelid
    join pg_am m
        on m.oid=i.relam
    join pg_class t
        on t.oid = ix.indrelid
    join pg_namespace n
        on n.oid = t.relnamespace
    join pg_attribute a
        on a.attrelid = t.oid
        and a.attnum = ANY(ix.indkey)
    where t.relname = '{{ relation.identifier }}'
      and n.nspname = '{{ relation.schema }}'
      and t.relkind in ('r', 'm')
    group by 1, 2, 3
    order by 1, 2, 3
{% endmacro %}


{%- macro postgres__get_drop_index_sql(relation, index_name) -%}
    drop index if exists "{{ relation.schema }}"."{{ index_name }}"
{%- endmacro -%}
