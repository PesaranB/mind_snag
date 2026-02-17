"""Tests for params.py loader."""

from mind_snag.io.params_py_loader import load_params_py


def test_load_params_py(tmp_path):
    params_file = tmp_path / "params.py"
    params_file.write_text(
        "sample_rate = 30000.0\n"
        "n_channels_dat = 385\n"
        "dtype = 'int16'\n"
        "hp_filtered = True\n"
        "# This is a comment\n"
        "offset = 0\n"
    )
    params = load_params_py(params_file)
    assert params["sample_rate"] == 30000.0
    assert params["n_channels_dat"] == 385
    assert params["dtype"] == "int16"
    assert params["hp_filtered"] is True
    assert params["offset"] == 0


def test_empty_params(tmp_path):
    params_file = tmp_path / "params.py"
    params_file.write_text("# empty file\n")
    params = load_params_py(params_file)
    assert params == {}
