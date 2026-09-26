"""Tier 2: OBS drag-trail rendering and lifecycle."""

from unittest.mock import MagicMock, call

import pytest

from tests.conftest import Vec2


def test_show_trail_segment_creates_color_source(obs_script, mock_obs):
    del mock_obs.OBS_ALIGN_CENTER
    mock_obs.obs_scene_find_source.return_value = None
    mock_obs.obs_get_source_by_name.return_value = None

    shown = obs_script._show_trail_segment(
        "__click_pop_TRAIL_L_0", obs_script._TRAIL_LEFT_COLOR,
        10, 20, 30, 20, 8,
    )

    assert shown is True
    assert mock_obs.obs_source_create.call_args[0][:2] == (
        "color_source_v3", "__click_pop_TRAIL_L_0",
    )
    settings = mock_obs._created_settings
    mock_obs.obs_data_set_int.assert_has_calls([
        call(settings, "color", 0xFF0000FF),
        call(settings, "width", 1),
        call(settings, "height", 1),
    ])
    mock_obs.obs_sceneitem_set_alignment.assert_called_once_with(
        mock_obs._created_item, obs_script._OBS_ALIGN_CENTER,
    )
    pos = mock_obs.obs_sceneitem_set_pos.call_args[0][1]
    scale = mock_obs.obs_sceneitem_set_scale.call_args[0][1]
    assert isinstance(pos, Vec2)
    assert (pos.x, pos.y) == pytest.approx((20, 20))
    assert isinstance(scale, Vec2)
    assert (scale.x, scale.y) == pytest.approx((28, 8))
    mock_obs.obs_sceneitem_set_rot.assert_called_once_with(
        mock_obs._created_item, 0,
    )
    mock_obs.obs_sceneitem_set_visible.assert_called_once_with(
        mock_obs._created_item, True,
    )


def test_show_trail_segment_updates_existing_source(obs_script, mock_obs):
    scene_item = MagicMock(name="trail_item")
    mock_obs.obs_scene_find_source.return_value = scene_item

    obs_script._show_trail_segment(
        "__click_pop_TRAIL_R_0", obs_script._TRAIL_RIGHT_COLOR,
        0, 0, 0, 20, 4,
    )

    mock_obs.obs_source_update.assert_called_once_with(
        mock_obs._scene_item_source, mock_obs._existing_settings,
    )
    mock_obs.obs_sceneitem_set_rot.assert_called_once_with(scene_item, 90)


def test_spawn_trail_rejects_different_capture_routes(obs_script, monkeypatch):
    left_display = {
        "id": 1, "x": 0, "y": 0, "w": 1920, "h": 1080,
        "retina_scale": 1.0,
    }
    right_display = {
        "id": 2, "x": 1920, "y": 0, "w": 1920, "h": 1080,
        "retina_scale": 1.0,
    }
    obs_script._all_displays = [left_display, right_display]
    obs_script._multi_capture_mode = True
    obs_script._display_capture_map = {
        1: {"display": left_display, "source_name": "Display Capture 1"},
        2: {"display": right_display, "source_name": "Display Capture 2"},
    }
    monkeypatch.setattr(obs_script, "_get_capture_transform", lambda *args: None)
    show = MagicMock()
    monkeypatch.setattr(obs_script, "_show_trail_segment", show)

    obs_script._spawn_trail_segment(1900, 500, 1940, 500, True, 99)

    show.assert_not_called()
    assert not obs_script._active_trails


def test_trail_pool_reuses_source_without_removing_it(obs_script, monkeypatch):
    monkeypatch.setattr(obs_script, "_TRAIL_MAX_SEGMENTS", 1)
    monkeypatch.setattr(
        obs_script, "_map_desktop_point", lambda x, y: (x, y, (None, "")),
    )
    monkeypatch.setattr(obs_script, "_show_trail_segment", lambda *args: True)
    obs_script._active_clicks.append(("__click_pop_L_0", 50))
    obs_script._active_trails.append(("__click_pop_TRAIL_L_0", 40))

    obs_script._spawn_trail_segment(0, 0, 20, 0, True, 60)

    assert obs_script._active_clicks == [("__click_pop_L_0", 50)]
    assert obs_script._active_trails == [("__click_pop_TRAIL_L_0", 60)]


def test_poll_drains_and_expires_trails(obs_script, monkeypatch):
    spawn = MagicMock()
    hide = MagicMock()
    monkeypatch.setattr(obs_script, "_spawn_trail_segment", spawn)
    monkeypatch.setattr(obs_script, "_hide_source", hide)
    monkeypatch.setattr(obs_script.time, "time", lambda: 10.0)
    obs_script._settings["trail_duration_ms"] = 300
    obs_script._trail_queue.append((0, 0, 20, 0, True, 9.5))
    obs_script._active_clicks.append(("old_click", 10.0))
    obs_script._active_trails.append(("old_trail", 10.0))

    obs_script._poll_clicks()

    spawn.assert_called_once_with(0, 0, 20, 0, True, 9.8)
    assert hide.call_args_list == [call("old_click"), call("old_trail")]
    assert not obs_script._active_trails