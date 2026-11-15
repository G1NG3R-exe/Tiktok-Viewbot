import asyncio

from bot.runner import _ProxyRotator


def test_rotator_uses_every_proxy_before_repeating():
    proxies = ["a:1", "b:2", "c:3"]
    rotator = _ProxyRotator(list(proxies))

    first_wave = [asyncio.run(rotator.next()) for _ in range(3)]
    assert sorted(first_wave) == sorted(proxies)

    second_wave = [asyncio.run(rotator.next()) for _ in range(3)]
    assert sorted(second_wave) == sorted(proxies)


def test_rotator_without_proxies_returns_none():
    assert asyncio.run(_ProxyRotator([]).next()) is None


def test_rotator_retires_proxies_after_two_failures():
    rotator = _ProxyRotator(["a:1"])

    assert asyncio.run(rotator.next()) == "a:1"
    rotator.fail("a:1")
    assert asyncio.run(rotator.next()) == "a:1"
    rotator.fail("a:1")

    # retired -> direct connection
    assert asyncio.run(rotator.next()) is None
