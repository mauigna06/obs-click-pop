"""Tier 2: OBS drag-trail settings wiring."""

from unittest.mock import MagicMock, call


def test_script_properties_adds_trail_controls(obs_script, mock_obs, monkeypatch):
    props = MagicMock(name="props")
    mock_obs.obs_properties_create.return_value = props
    monkeypatch.setattr(obs_script, "_populate_capture_list", lambda prop: None)
    monkeypatch.setattr(obs_script, "_add_display_info", lambda owner: None)

    result = obs_script.script_properties()

    assert result is props
    mock_obs.obs_properties_add_bool.assert_any_call(
        props, "trail_enabled", "Show drag trails",
    )
    mock_obs.obs_properties_add_bool.assert_any_call(
        props, "cursor_trail_enabled", "Show trail for all cursor movement",
    )
    mock_obs.obs_properties_add_int.assert_any_call(
        props, "trail_width", "Trail line width (px)", 1, 40, 1,
    )
    mock_obs.obs_properties_add_int.assert_any_call(
        props, "trail_duration_ms", "Trail duration (ms)", 100, 2000, 50,
    )
    mock_obs.obs_properties_add_int.assert_any_call(
        props, "trail_spacing", "Trail sampling distance (px)", 2, 100, 1,
    )


def test_script_defaults_include_trail_settings(obs_script, mock_obs, monkeypatch):
    monkeypatch.setattr(obs_script, "_detect_screen_size", lambda: (1920, 1080))
    settings = MagicMock(name="settings")

    obs_script.script_defaults(settings)

    mock_obs.obs_data_set_default_bool.assert_any_call(
        settings, "trail_enabled", True,
    )
    mock_obs.obs_data_set_default_bool.assert_any_call(
        settings, "cursor_trail_enabled", False,
    )
    mock_obs.obs_data_set_default_int.assert_has_calls([
        call(settings, "trail_width", 8),
        call(settings, "trail_duration_ms", 350),
        call(settings, "trail_spacing", 10),
    ])


def test_script_update_reads_trail_settings_and_clears_disabled_queue(
        obs_script, mock_obs, monkeypatch):
    monkeypatch.setattr(obs_script, "_refresh_displays", lambda: None)
    mock_obs.obs_data_get_bool.side_effect = lambda settings, name: {
        "trail_enabled": False,
        "cursor_trail_enabled": True,
        "override_monitor": True,
    }.get(name, False)
    mock_obs.obs_data_get_int.side_effect = lambda settings, name: {
        "trail_width": 12,
        "trail_duration_ms": 600,
        "trail_spacing": 18,
        "duration_ms": 350,
        "circle_size": 60,
        "monitor_w": 1920,
        "monitor_h": 1080,
        "max_circles": 5,
    }.get(name, 0)
    obs_script._trail_queue.append((0, 0, 10, 0, True, 1.0))

    obs_script.script_update(MagicMock(name="settings"))

    assert obs_script._settings["trail_enabled"] is False
    assert obs_script._settings["cursor_trail_enabled"] is True
    assert obs_script._settings["trail_width"] == 12
    assert obs_script._settings["trail_duration_ms"] == 600
    assert obs_script._settings["trail_spacing"] == 18
    assert not obs_script._trail_queue


def test_trail_toggle_updates_dependent_property_visibility(obs_script, mock_obs):
    props = MagicMock(name="props")
    settings = MagicMock(name="settings")
    fields = {
        "cursor_trail_enabled": MagicMock(name="cursor_trail_enabled"),
        "trail_width": MagicMock(name="trail_width"),
        "trail_duration_ms": MagicMock(name="trail_duration_ms"),
        "trail_spacing": MagicMock(name="trail_spacing"),
    }
    mock_obs.obs_data_get_bool.return_value = False
    mock_obs.obs_properties_get.side_effect = lambda owner, name: fields[name]

    changed = obs_script._on_trail_toggle(props, None, settings)

    assert changed is True
    for field in fields.values():
        mock_obs.obs_property_set_visible.assert_any_call(field, False)