opts=( -f -k -v )

while true; do
    case "$1" in
        --dry-run )
            opts+=( -n )
            shift 1
        ;;
        * )
            break
        ;;
    esac
done

rm -r dbt-postgres
mkdir dbt-postgres

declare -a sources=(".changes" "docker" "scripts" "tests" ".changie.yaml" "CHANGELOG.md" "CONTRIBUTING.md" "pyproject.toml" "README.md" "test.env.example")
for source in "${sources[@]}"
do
    git mv "${opts[@]}" $source dbt-postgres
done

mkdir dbt-postgres/src
git mv "${opts[@]}" dbt dbt-postgres/src
git mv "${opts[@]}" dbt-postgres/test.env.example dbt-postgres/.env.example
git mv "${opts[@]}" .github/scripts/psycopg2-check.sh dbt-postgres/scripts/psycopg2-check.sh
