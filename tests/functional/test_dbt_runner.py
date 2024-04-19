from unittest import mock

from dbt.cli.exceptions import DbtUsageException
from dbt.cli.main import dbtRunner
from dbt.exceptions import DbtProjectError
import pytest


class TestDbtRunner:
    @pytest.fixture
    def dbt(self) -> dbtRunner:
        return dbtRunner()

    def test_group_invalid_option(self, dbt: dbtRunner) -> None:
        res = dbt.invoke(["--invalid-option"])
        assert isinstance(res.exception, DbtUsageException)

    def test_command_invalid_option(self, dbt: dbtRunner) -> None:
        res = dbt.invoke(["deps", "--invalid-option"])
        assert isinstance(res.exception, DbtUsageException)

    def test_command_mutually_exclusive_option(self, dbt: dbtRunner) -> None:
        res = dbt.invoke(["--warn-error", "--warn-error-options", '{"include": "all"}', "deps"])
        assert isinstance(res.exception, DbtUsageException)
        res = dbt.invoke(["deps", "--warn-error", "--warn-error-options", '{"include": "all"}'])
        assert isinstance(res.exception, DbtUsageException)

    def test_invalid_command(self, dbt: dbtRunner) -> None:
        res = dbt.invoke(["invalid-command"])
        assert isinstance(res.exception, DbtUsageException)

    def test_invoke_version(self, dbt: dbtRunner) -> None:
        dbt.invoke(["--version"])

    def test_callbacks(self) -> None:
        mock_callback = mock.MagicMock()
        dbt = dbtRunner(callbacks=[mock_callback])
        # the `debug` command is one of the few commands wherein you don't need
        # to have a project to run it and it will emit events
        dbt.invoke(["debug"])
        mock_callback.assert_called()

    def test_invoke_kwargs(self, project, dbt):
        res = dbt.invoke(
            ["run"],
            log_format="json",
            log_path="some_random_path",
            version_check=False,
            profile_name="some_random_profile_name",
            target_dir="some_random_target_dir",
        )
        assert res.result.args["log_format"] == "json"
        assert res.result.args["log_path"] == "some_random_path"
        assert res.result.args["version_check"] is False
        assert res.result.args["profile_name"] == "some_random_profile_name"
        assert res.result.args["target_dir"] == "some_random_target_dir"

    def test_invoke_kwargs_project_dir(self, project, dbt):
        res = dbt.invoke(["run"], project_dir="some_random_project_dir")
        assert isinstance(res.exception, DbtProjectError)

        msg = "No dbt_project.yml found at expected path some_random_project_dir"
        assert msg in res.exception.msg

    def test_invoke_kwargs_profiles_dir(self, project, dbt):
        res = dbt.invoke(["run"], profiles_dir="some_random_profiles_dir")
        assert isinstance(res.exception, DbtProjectError)
        msg = "Could not find profile named 'test'"
        assert msg in res.exception.msg

    def test_invoke_kwargs_and_flags(self, project, dbt):
        res = dbt.invoke(["--log-format=text", "run"], log_format="json")
        assert res.result.args["log_format"] == "json"
