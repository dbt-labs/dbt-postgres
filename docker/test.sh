# - VERY rudimentary test script to run latest + specific branch image builds and test them all by running `--version`
# TODO: create a real test suite

clear \
&& echo "\n\n"\
"########################################\n"\
"##### Testing dbt-postgres latest #####\n"\
"########################################\n"\
&& docker build --tag dbt-postgres \
  --target dbt-postgres \
  docker \
&& docker run dbt-postgres --version \
\
&& echo "\n\n"\
"#########################################\n"\
"##### Testing dbt-postgres-1.0.0b1 #####\n"\
"#########################################\n"\
&& docker build --tag dbt-postgres-1.0.0b1 \
  --target dbt-postgres \
  --build-arg dbt_postgres_ref=dbt-postgres@v1.0.0b1 \
  docker \
&& docker run dbt-postgres-1.0.0b1 --version
