from application_tracker.ui.scale_settings import load_scale, save_scale


def test_scale_preference_round_trip_and_invalid_fallback(tmp_path):
    path = tmp_path / "ui.ini"
    assert load_scale(path) == 1.0
    save_scale(path, 2.0)
    assert load_scale(path) == 2.0
    path.write_text("[ui]\nscale = 3.0\n", encoding="utf-8")
    assert load_scale(path) == 1.0
