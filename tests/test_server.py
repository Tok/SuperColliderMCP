import asyncio

import pytest
from mcp import Client

from supercollidermcp.engine import FX_GROUP, LIMITER, ROOT_GROUP, SOURCE_GROUP, Engine
from supercollidermcp.osc import SCClient
from supercollidermcp.server import create_server
from supercollidermcp.synthdefs import compiled_synthdefs

pytestmark = pytest.mark.anyio

EVERY_TOOL = {
    "play_example_osc": {},
    "play_synth": {"synth_type": "fm", "note": "C4", "duration": 0.5},
    "create_layered_synth": {"duration": 1},
    "create_lfo_modulation": {"target_param": "amplitude", "duration": 1},
    "create_granular_texture": {"duration": 1, "seed": 1},
    "play_melody": {"notes": 4, "seed": 2},
    "create_sequence": {"pattern": "C4 E4 G4"},
    "create_chord_progression": {"progression": "C-F", "duration_per_chord": 1},
    "create_drum_pattern": {"bars": 1},
    "create_generative_rhythm": {"duration": 4, "seed": 3},
    "create_ambient_soundscape": {"duration": 5, "seed": 4},
}


@pytest.fixture
async def session(fake_scsynth):
    engine = Engine(SCClient("127.0.0.1", fake_scsynth.port, timeout=0.3), latency=0.05, lookahead=0.3)
    async with Client(create_server(engine)) as client:
        yield client, fake_scsynth, engine
    engine.client.close()


async def call(client, name, args=None):
    result = await client.call_tool(name, args or {})
    return result.is_error, result.content[0].text


async def test_tool_list_and_schemas():
    tools = {t.name: t for t in await create_server().list_tools()}
    assert set(tools) == {*EVERY_TOOL, "server_status", "stop_all"}
    props = tools["play_synth"].input_schema["properties"]
    assert props["duration"]["type"] == "number"  # v0.1 advertised every parameter as a string
    assert props["synth_type"]["enum"] == ["sine", "saw", "square", "noise", "fm", "pad", "pluck"]
    assert tools["create_sequence"].input_schema["required"] == ["pattern"]
    assert tools["server_status"].annotations.read_only_hint is True


async def test_first_call_installs_synthdefs_and_groups(session):
    client, fake, _ = session
    error, text = await call(client, "play_example_osc")
    assert not error, text
    addresses = fake.addresses()
    assert addresses.count("/d_recv") == len(compiled_synthdefs())
    group_news = [args for address, args in fake.messages if address == "/g_new"]
    assert group_news == [[ROOT_GROUP, 0, 0], [SOURCE_GROUP, 0, ROOT_GROUP], [FX_GROUP, 3, SOURCE_GROUP]]
    assert ("/s_new", ["mcp_limiter", LIMITER, 1, ROOT_GROUP]) in fake.messages
    # a sync must separate the SynthDef upload from the first use of a SynthDef
    assert addresses.index("/sync") < addresses.index("/s_new")

    await call(client, "play_example_osc")
    assert fake.addresses().count("/d_recv") == len(compiled_synthdefs()), "set up only once"


async def test_synthdefs_are_refreshed_when_another_session_set_up_the_server(fake_scsynth):
    first = Engine(SCClient("127.0.0.1", fake_scsynth.port))
    await first.ensure_ready()
    second = Engine(SCClient("127.0.0.1", fake_scsynth.port))  # e.g. after upgrading the package
    await second.ensure_ready()
    await second.ensure_ready()
    assert fake_scsynth.addresses().count("/d_recv") == 2 * len(compiled_synthdefs())
    assert fake_scsynth.addresses().count("/g_new") == 3, "existing groups must be left alone"
    first.client.close()
    second.client.close()


async def test_restarted_server_is_set_up_again(session):
    client, fake, _ = session
    await call(client, "play_example_osc")
    fake.nodes.clear()  # simulate a scsynth restart
    await call(client, "play_example_osc")
    assert fake.addresses().count("/d_recv") == 2 * len(compiled_synthdefs())


@pytest.mark.parametrize("name", list(EVERY_TOOL))
async def test_every_tool_schedules_sound_and_returns_immediately(session, name):
    client, fake, engine = session
    loop = asyncio.get_running_loop()
    started = loop.time()
    error, text = await call(client, name, EVERY_TOOL[name])
    assert not error, text
    assert loop.time() - started < 0.5, "tools must not block while the sound plays"
    assert text.startswith("Playing ")
    await asyncio.sleep(0.4)
    scheduled = fake.scheduled()
    assert scheduled, "nothing was sent to the server"
    for address, args in scheduled:
        assert address == "/s_new"
        assert args[0].startswith("mcp_") and args[1] == -1 and args[3] in (SOURCE_GROUP, FX_GROUP)
    await engine.stop_all()


async def test_effects_add_fx_synth_on_private_bus(session):
    client, fake, engine = session
    error, text = await call(client, "play_synth", {"duration": 0.2, "effects": {"reverb": 0.6, "delay": 0.2}})
    assert not error, text
    assert "reverb 0.60, delay 0.20" in text
    await asyncio.sleep(0.2)
    fx = [args for _, args in fake.scheduled() if args[0] == "mcp_fx"]
    voice = [args for _, args in fake.scheduled() if args[0] == "mcp_sine"]
    assert len(fx) == 1 and fx[0][3] == FX_GROUP
    bus = fx[0][fx[0].index("in") + 1]
    assert voice[0][voice[0].index("out") + 1] == bus >= 512
    await engine.stop_all()


async def test_seed_is_reported_and_reproducible(session):
    client, _, engine = session
    _, first = await call(client, "play_melody", {"notes": 6})
    seed = int(first.rsplit("seed=", 1)[1])
    _, again = await call(client, "play_melody", {"notes": 6, "seed": seed})
    assert first.splitlines()[1:] == again.splitlines()[1:]
    await engine.stop_all()


@pytest.mark.parametrize(
    ("name", "args", "message"),
    [
        ("play_synth", {"note": "H9"}, "not a note name"),
        ("play_synth", {"volume": 3}, "less than or equal to 1"),
        ("create_sequence", {"pattern": "C4 Q9"}, "cannot parse"),
        ("create_chord_progression", {"progression": "C-Xyz"}, "unknown chord"),
        ("create_drum_pattern", {"custom": {"kick": "x-x-"}}, "characters"),
        ("create_lfo_modulation", {"target_param": "filter", "synth": "sine"}, "has no filter"),
        ("play_melody", {"root": "Z"}, "not a note name"),
    ],
)
async def test_bad_input_is_a_tool_error(session, name, args, message):
    client, fake, _ = session
    error, text = await call(client, name, args)
    assert error and message in text
    assert not fake.bundles


async def test_unreachable_server(session):
    client, fake, _ = session
    fake.silent = True
    error, text = await call(client, "play_example_osc")
    assert error and "Is scsynth running" in text
    error, text = await call(client, "server_status")
    assert not error and "Is scsynth running" in text


async def test_status_and_stop_all(session):
    client, fake, engine = session
    await call(client, "create_ambient_soundscape", {"duration": 30, "seed": 1})
    error, text = await call(client, "server_status")
    assert not error
    assert "scsynth 3.13.0" in text and "1 playback(s) running" in text and "ambient" in text

    error, text = await call(client, "stop_all")
    assert not error and "Stopped 1 playback" in text
    await asyncio.sleep(0.05)  # UDP is fire-and-forget; let the datagrams arrive
    assert fake.messages[-3:] == [("/clearSched", []), ("/g_freeAll", [SOURCE_GROUP]), ("/g_freeAll", [FX_GROUP])]
    assert engine.active() == []
