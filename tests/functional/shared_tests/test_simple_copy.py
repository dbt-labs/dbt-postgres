from dbt.tests.adapter.simple_copy.test_simple_copy import BaseSimpleCopyUppercase
from dbt.tests.adapter.simple_copy.test_copy_uppercase import (
    SimpleCopyBase,
    EmptyModelsArentRunBase,
)


class TestSimpleCopyUppercase(BaseSimpleCopyUppercase):
    pass


class TestSimpleCopyBase(SimpleCopyBase):
    pass


class TestEmptyModelsArentRun(EmptyModelsArentRunBase):
    pass
