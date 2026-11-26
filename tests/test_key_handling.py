"""A wrong or malformed validator key fails loudly, and never shows up in the error."""
import traceback

import pytest
from eth_account import Account

from replay8004 import registry
from replay8004.lambda_handler import make_sender
from tests.conftest import FakeRpc


@pytest.mark.parametrize("bad", ["\x16", "0x" + "ab" * 20, "not-a-key-but-secret-looking-9f8e7d", "0x" + "zz" * 32])
def test_malformed_key_never_appears_in_the_error(bad):
    with pytest.raises(ValueError) as e:
        registry.Sender(FakeRpc(), 11142220, bad)
    shown = "".join(traceback.format_exception(e.value))
    assert bad not in shown and "valid private key" in shown
    assert e.value.__cause__ is None and e.value.__suppress_context__


def test_lambda_refuses_a_key_for_another_validator():
    right, wrong = Account.create(), Account.create()   # throwaway keys, never funded
    assert make_sender(FakeRpc(), 11142220, right.key.hex(), right.address.lower()).address == right.address
    with pytest.raises(RuntimeError) as e:
        make_sender(FakeRpc(), 11142220, wrong.key.hex(), right.address)
    msg = str(e.value)
    assert wrong.address in msg and right.address in msg
    assert wrong.key.hex().removeprefix("0x") not in msg
