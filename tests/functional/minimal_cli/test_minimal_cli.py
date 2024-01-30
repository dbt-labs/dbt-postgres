from dbt.cli.main import cli

from tests.functional.minimal_cli.fixtures import BaseConfigProject
from tests.functional.utils import up_one


class TestClean(BaseConfigProject):
    """Test the minimal/happy-path for the CLI using the Click CliRunner"""

    def test_clean(self, runner, project):
        result = runner.invoke(cli, ["clean"])
        assert "target" in result.output
        assert "dbt_packages" in result.output
        assert "logs" in result.output


class TestCleanUpLevel(BaseConfigProject):
    def test_clean_one_level_up(self, runner, project):
        with up_one():
            result = runner.invoke(cli, ["clean"])
            assert result.exit_code == 2
            assert "Runtime Error" in result.output
            assert "No dbt_project.yml" in result.output


class TestDeps(BaseConfigProject):
    def test_deps(self, runner, project):
        result = runner.invoke(cli, ["deps"])
        assert "dbt-labs/dbt_utils" in result.output
        assert "1.0.0" in result.output


class TestBuild(BaseConfigProject):
    def test_build(self, runner, project):
        runner.invoke(cli, ["deps"])
        result = runner.invoke(cli, ["build"])
        # 1 seed, 1 model, 2 data tests
        assert "PASS=4" in result.output
        # 2 data tests
        assert "ERROR=2" in result.output
        # Singular test
        assert "WARN=1" in result.output
        # 1 snapshot
        assert "SKIP=1" in result.output


class TestDocsGenerate(BaseConfigProject):
    def test_docs_generate(self, runner, project):
        runner.invoke(cli, ["deps"])
        result = runner.invoke(cli, ["docs", "generate"])
        assert "Building catalog" in result.output
        assert "Catalog written" in result.output
