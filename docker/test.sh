# - VERY rudimentary test script to run latest + specific branch image builds and test them all by running `--version`
# TODO: create a real test suite
set -e

echo "\n\n"
echo "#######################################"
echo "##### Testing dbt-postgres latest #####"
echo "#######################################"

docker build --tag dbt-postgres --target dbt-postgres docker
docker run dbt-postgres --version

echo "\n\n"
echo "########################################"
echo "##### Testing dbt-postgres-1.0.0b1 #####"
echo "########################################"

docker build --tag dbt-postgres-1.0.0b1 --target dbt-postgres --build-arg commit_ref=v1.0.0b1 docker
docker run dbt-postgres-1.0.0b1 --version
