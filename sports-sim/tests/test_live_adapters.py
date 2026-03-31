from sports_sim.adapters.live_feed import LiveAdapter


def test_live_adapter_callbacks():
    called = []

    def cb(msg):
        called.append(msg)

    a = LiveAdapter()
    a.register_callback(cb)
    a._emit({"type": "test", "payload": 1})
    assert called and called[0]["type"] == "test"
