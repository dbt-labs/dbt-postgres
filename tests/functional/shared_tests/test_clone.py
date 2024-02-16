from dbt.tests.adapter.dbt_clone.test_dbt_clone import (
    BaseCloneNotPossible,
    BaseClonePossible,
    BaseCloneSameTargetAndState,
)


class TestBaseCloneNotPossible(BaseCloneNotPossible):
    pass


class TestBaseClonePossible(BaseClonePossible):
    pass


class TestCloneSameTargetAndState(BaseCloneSameTargetAndState):
    pass
