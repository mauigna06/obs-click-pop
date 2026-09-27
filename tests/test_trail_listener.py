"""Tier 2: pynput drag gesture capture."""

import sys
from types import ModuleType, SimpleNamespace

import pytest


class FakeListener:
    latest = None

    def __init__(self, **callbacks):
        self.callbacks = callbacks
        self.daemon = False
        self.started = False
        FakeListener.latest = self

    def start(self):
        self.started = True

    def stop(self):
        pass


@pytest.fixture()
def mouse_buttons(monkeypatch):
    buttons = SimpleNamespace(left=object(), right=object(), middle=object())
    mouse_module = ModuleType("pynput.mouse")
    mouse_module.Listener = FakeListener
    mouse_module.Button = buttons
    pynput_module = ModuleType("pynput")
    pynput_module.mouse = mouse_module
    monkeypatch.setitem(sys.modules, "pynput", pynput_module)
    monkeypatch.setitem(sys.modules, "pynput.mouse", mouse_module)
    return buttons


def start_callbacks(obs_script, mouse_buttons, *, cursor_trail_enabled=False):
    obs_script._settings["trail_enabled"] = True
    obs_script._settings["cursor_trail_enabled"] = cursor_trail_enabled
    obs_script._settings["trail_spacing"] = 10
    obs_script._start_listener()
    return FakeListener.latest.callbacks


def test_plain_move_does_not_enqueue_trail(obs_script, mouse_buttons):
    callbacks = start_callbacks(obs_script, mouse_buttons)

    callbacks["on_move"](20, 20)

    assert not obs_script._trail_queue


def test_plain_move_enqueues_trail_when_cursor_trail_enabled(
        obs_script, mouse_buttons, monkeypatch):
    monkeypatch.setattr(obs_script.time, "time", lambda: 12.5)
    callbacks = start_callbacks(
        obs_script, mouse_buttons, cursor_trail_enabled=True,
    )

    callbacks["on_move"](10, 20)
    callbacks["on_move"](19, 20)
    assert not obs_script._trail_queue
    callbacks["on_move"](20, 20)

    assert list(obs_script._trail_queue) == [(10, 20, 20, 20, True, 12.5)]


def test_cursor_trail_does_not_duplicate_drag(obs_script, mouse_buttons):
    callbacks = start_callbacks(
        obs_script, mouse_buttons, cursor_trail_enabled=True,
    )

    callbacks["on_move"](0, 0)
    callbacks["on_click"](0, 0, mouse_buttons.left, True)
    callbacks["on_move"](10, 0)

    assert len(obs_script._trail_queue) == 1
    assert obs_script._trail_queue[0][:5] == (0, 0, 10, 0, True)


def test_press_keeps_click_and_threshold_move_enqueues_trail(
        obs_script, mouse_buttons, monkeypatch):
    monkeypatch.setattr(obs_script.time, "time", lambda: 12.5)
    callbacks = start_callbacks(obs_script, mouse_buttons)

    callbacks["on_click"](10, 20, mouse_buttons.left, True)
    callbacks["on_move"](19, 20)
    assert not obs_script._trail_queue
    callbacks["on_move"](20, 20)

    assert list(obs_script._click_queue) == [(10, 20, True, 12.5)]
    assert list(obs_script._trail_queue) == [(10, 20, 20, 20, True, 12.5)]


def test_release_flushes_short_final_segment(obs_script, mouse_buttons):
    callbacks = start_callbacks(obs_script, mouse_buttons)

    callbacks["on_click"](10, 20, mouse_buttons.right, True)
    callbacks["on_move"](20, 20)
    callbacks["on_click"](24, 20, mouse_buttons.right, False)

    segments = list(obs_script._trail_queue)
    assert segments[0][:5] == (10, 20, 20, 20, False)
    assert segments[1][:5] == (20, 20, 24, 20, False)


def test_left_and_right_drag_state_is_independent(obs_script, mouse_buttons):
    callbacks = start_callbacks(obs_script, mouse_buttons)

    callbacks["on_click"](0, 0, mouse_buttons.left, True)
    callbacks["on_click"](100, 0, mouse_buttons.right, True)
    callbacks["on_move"](110, 0)

    segments = list(obs_script._trail_queue)
    assert segments[0][:5] == (0, 0, 110, 0, True)
    assert segments[1][:5] == (100, 0, 110, 0, False)


def test_middle_button_has_click_marker_but_no_trail(obs_script, mouse_buttons):
    callbacks = start_callbacks(obs_script, mouse_buttons)

    callbacks["on_click"](10, 20, mouse_buttons.middle, True)
    callbacks["on_move"](30, 20)
    callbacks["on_click"](30, 20, mouse_buttons.middle, False)

    assert len(obs_script._click_queue) == 1
    assert obs_script._click_queue[0][2] is False
    assert not obs_script._trail_queue


def test_disabling_trails_stops_active_drag(obs_script, mouse_buttons):
    callbacks = start_callbacks(obs_script, mouse_buttons)
    callbacks["on_click"](0, 0, mouse_buttons.left, True)

    obs_script._settings["trail_enabled"] = False
    callbacks["on_move"](20, 0)
    obs_script._settings["trail_enabled"] = True
    callbacks["on_move"](40, 0)
    callbacks["on_click"](40, 0, mouse_buttons.left, False)

    assert not obs_script._trail_queue