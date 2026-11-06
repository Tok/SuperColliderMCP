import time

import pytest

from supercollidermcp.osc import SCClient, SCError, ServerUnreachable, encode_message

pytestmark = pytest.mark.anyio


async def test_status_and_version(fake_scsynth):
    client = SCClient("127.0.0.1", fake_scsynth.port)
    status = await client.status()
    assert status.nominal_sample_rate == 48000.0 and status.peak_cpu == 2.5
    assert await client.version() == "3.13.0"
    client.close()


async def test_sync_matches_its_own_id(fake_scsynth):
    client = SCClient("127.0.0.1", fake_scsynth.port)
    await client.sync()
    await client.sync()
    assert [args for address, args in fake_scsynth.messages if address == "/sync"] == [[1], [2]]
    client.close()


async def test_existence_checks_use_commands_that_answer_the_sender(fake_scsynth):
    client = SCClient("127.0.0.1", fake_scsynth.port)
    assert not await client.synth_exists(1234, "level")
    assert not await client.group_exists(99)
    fake_scsynth.nodes |= {1234, 99}
    assert await client.synth_exists(1234, "level")
    assert await client.group_exists(99)
    assert "/n_query" not in fake_scsynth.addresses()
    assert client.recent_errors[0] == "/s_get Node 1234 not found"
    client.close()


async def test_unreachable_server_gives_a_helpful_error(fake_scsynth):
    fake_scsynth.silent = True
    client = SCClient("127.0.0.1", fake_scsynth.port, timeout=0.2)
    with pytest.raises(ServerUnreachable, match="Is scsynth running"):
        await client.status()
    client.close()


async def test_nothing_listening_fails_fast():
    client = SCClient("127.0.0.1", 9, timeout=2.0)  # discard port: nothing listens there
    started = time.monotonic()
    with pytest.raises(ServerUnreachable):
        await client.status()
    assert time.monotonic() - started < 2.5
    client.close()


async def test_bundles_carry_their_timestamp(fake_scsynth):
    client = SCClient("127.0.0.1", fake_scsynth.port)
    due = time.time() + 1.5
    await client.send_bundle(due, [("/s_new", ["mcp_sine", -1, 1, 5, "freq", 440.0])])
    await client.status()  # round trip so the bundle has surely arrived
    ((timestamp, contents),) = fake_scsynth.bundles
    assert timestamp == pytest.approx(due, abs=1e-3)
    assert contents == [("/s_new", ["mcp_sine", -1, 1, 5, "freq", 440.0])]
    client.close()


def test_encode_message_types():
    message = encode_message("/x", [1, 2.5, "s", b"\x00\x01", True])
    assert list(message.params) == [1, 2.5, "s", b"\x00\x01", 1]
    with pytest.raises(TypeError):
        encode_message("/x", [None])


def test_scerror_hierarchy():
    assert issubclass(ServerUnreachable, SCError)
