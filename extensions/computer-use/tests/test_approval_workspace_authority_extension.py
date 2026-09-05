import inspect

import imperaos_computer_use.runtime as computer_use_runtime


def test_computer_use_does_not_bypass_scoped_runtime_lookup() -> None:
    assert ".approval_store.get(" not in inspect.getsource(computer_use_runtime)
