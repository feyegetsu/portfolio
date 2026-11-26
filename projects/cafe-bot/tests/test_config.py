"""BOT-001: без BOT_TOKEN и ADMIN_ID бот не стартует, а не теряет заказы молча."""

import pytest

import bot as cafe


@pytest.mark.parametrize("env, missing", [
    ({}, ["BOT_TOKEN", "ADMIN_ID"]),
    ({"BOT_TOKEN": "123:abc"}, ["ADMIN_ID"]),
    ({"BOT_TOKEN": "123:abc", "ADMIN_ID": "мой id"}, ["ADMIN_ID"]),
    ({"BOT_TOKEN": "123:abc", "ADMIN_ID": "0"}, ["ADMIN_ID"]),
    ({"BOT_TOKEN": " ", "ADMIN_ID": "42"}, ["BOT_TOKEN"]),
])
def test_missing_settings_stop_the_bot(env, missing):
    with pytest.raises(SystemExit) as e:
        cafe.read_config(env)
    for name in missing:
        assert name in str(e.value.code)


def test_valid_settings():
    assert cafe.read_config({"BOT_TOKEN": "123:abc", "ADMIN_ID": " 42 "}) == ("123:abc", 42)
