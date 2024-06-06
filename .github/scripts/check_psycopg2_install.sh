python -m pip install .
PSYCOPG2_PIP_ENTRY=$(pip list | grep "psycopg2 " || pip list | grep psycopg2-binary)

echo $PSYCOPG2_PIP_ENTRY
PSYCOPG2_NAME="${PSYCOPG2_PIP_ENTRY%% *}"
echo $PSYCOPG2_NAME

if [[ "${PSYCOPG2_NAME}" != "${PSYCOPG2_EXPECTED_NAME}" ]]; then
    exit 1
fi
