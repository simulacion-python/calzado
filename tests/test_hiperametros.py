from tmp.main import main
import pytest


def test_main():

    assert main() == 123


@pytest.mark.xfail
def test_error():
    assert (1/0) == 1
