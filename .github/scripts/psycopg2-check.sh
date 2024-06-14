python -m venv venv
source venv/bin/activate
python -m pip install .

if [[ "$PSYCOPG2_WORKAROUND" == true ]]; then
    PSYCOPG2_VERSION=$(pip show --format=json | jq -r '.[] | select(.Name == "psycopg2-binary") | .Version')
    pip uninstall -y psycopg2-binary
    pip install psycopg2==$PSYCOPG2_VERSION
fi

PSYCOPG2_NAME=$(pip show --format=json | jq -r '.[] | select(.Name == "psycopg2" or .Name == "psycopg2-binary") | .name')
if [[ "$PSYCOPG2_NAME" != "$PSYCOPG2_EXPECTED_NAME" ]]; then
    echo -e 'Expected: "$PSYCOPG2_EXPECTED_NAME" but found: "$PSYCOPG2_NAME"'
    exit 1
fi

deactivate
rm -r ./venv
