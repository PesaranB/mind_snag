"""Execute Kilosort4 spike sorting on SpikeGLX recordings.

Ports run_kilosort4.m. Calls the kilosort Python API directly instead of
shelling out to a subprocess. Handles .bin file concatenation for grouped mode.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from mind_snag.config import MindSnagConfig
from mind_snag.io.mat_reader import load_mat
from mind_snag.utils.paths import group_rec_dir, rec_name_str

logger = logging.getLogger(__name__)


def run_kilosort4(
    cfg: MindSnagConfig,
    day: str,
    recs: list[str],
    tower: str,
    np_num: int,
    grouped: bool,
    override: bool = False,
) -> Path:
    """Execute Kilosort4 on SpikeGLX recordings.

    Parameters
    ----------
    cfg : pipeline configuration
    day : recording date (YYMMDD)
    recs : list of recording numbers
    tower : recording setup name
    np_num : probe number
    grouped : whether to concatenate recordings
    override : if True, re-concatenate even if combined file exists

    Returns
    -------
    Path to KS4 results directory
    """
    cfg.validate()
    data_root = cfg.data_root
    rec_str = rec_name_str(recs, grouped)

    # Create grouped recordings directory
    grp_dir = group_rec_dir(data_root, day, tower, np_num)
    grp_dir.mkdir(parents=True, exist_ok=True)

    # Concatenate input data if grouped
    if grouped:
        combined_bin = _concatenate_bins(
            cfg, day, recs, tower, np_num, rec_str, grp_dir, override,
        )
        input_data = combined_bin
    else:
        input_data = _find_single_rec_bin(cfg, day, recs[0], tower, np_num)

    # Create KS4 output directory
    ks_result_dir = grp_dir / f"group{rec_str}_KS4"
    ks_result_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Input: %s", input_data)
    logger.info("Output: %s", ks_result_dir)

    if not input_data.exists():
        raise FileNotFoundError(f"Input binary not found: {input_data}")

    # Run Kilosort4 via Python API
    _run_ks4_api(input_data, ks_result_dir, cfg)

    return ks_result_dir


def _concatenate_bins(
    cfg: MindSnagConfig,
    day: str,
    recs: list[str],
    tower: str,
    np_num: int,
    rec_str: str,
    grp_dir: Path,
    override: bool,
) -> Path:
    """Concatenate .ap.bin files from multiple recordings.

    Uses numpy memory mapping instead of MATLAB's sglx_util.memmap.
    """
    data_root = cfg.data_root

    ap_metas = []
    bin_files = []
    nsamp_total = 0

    for rec in recs:
        ap_meta_file = data_root / day / rec / f"rec{rec}.{tower}.{np_num}.ap_meta.mat"
        if not ap_meta_file.exists():
            raise FileNotFoundError(f"AP meta file not found: {ap_meta_file}")

        meta_data = load_mat(ap_meta_file)
        ap_meta = meta_data.get("ap_meta", {})
        ap_metas.append(ap_meta)

        nsamp = int(ap_meta.get("nsamp", 0)) if isinstance(ap_meta, dict) else int(getattr(ap_meta, "nsamp", 0))
        nsamp_total += nsamp

        # Find the .ap.bin file
        bin_path = _find_rec_bin(data_root, day, rec, ap_meta, np_num)
        bin_files.append(bin_path)

    # Get nchan from last meta
    nchan = int(ap_meta.get("nchan", 385)) if isinstance(ap_meta, dict) else int(getattr(ap_meta, "nchan", 385))

    # Output path
    group_input_dir = data_root / day / "spikeglx_data" / f"rec{rec_str}" / f"rec{rec_str}_imec{np_num - 1}"
    group_input_dir.mkdir(parents=True, exist_ok=True)
    combined_bin = group_input_dir / f"combined_ap_group{rec_str}.bin"

    expected_bytes = nsamp_total * nchan * 2  # int16

    if combined_bin.exists() and combined_bin.stat().st_size == expected_bytes and not override:
        logger.info("Combined AP file already exists: %s", combined_bin)
        return combined_bin

    logger.info("Concatenating %d recordings into %s", len(recs), combined_bin)

    with open(combined_bin, "wb") as fout:
        for i, (rec, bin_path) in enumerate(zip(recs, bin_files)):
            if not bin_path.exists():
                raise FileNotFoundError(f"Binary file not found: {bin_path}")
            meta = ap_metas[i]
            nsamp = int(meta.get("nsamp", 0)) if isinstance(meta, dict) else int(getattr(meta, "nsamp", 0))
            logger.info("  Memory mapping rec %s (%d samples)", rec, nsamp)

            # Memory-map and write in blocks
            mmap = np.memmap(bin_path, dtype=np.int16, mode="r",
                             shape=(nsamp, nchan))
            block_size = 500
            n_blocks = (nsamp + block_size - 1) // block_size
            for ib in range(n_blocks):
                start = ib * block_size
                end = min(nsamp, (ib + 1) * block_size)
                fout.write(mmap[start:end].tobytes())
            del mmap

    return combined_bin


def _find_rec_bin(
    data_root: Path, day: str, rec: str, ap_meta: dict, np_num: int,
) -> Path:
    """Find the .ap.bin file for a recording from its metadata."""
    if isinstance(ap_meta, dict):
        probe_name = ap_meta.get("imec_used_probe_name") or ap_meta.get("used_probe_name") or f"imec{np_num - 1}"
        file_name = ap_meta.get("fileName", "")
    else:
        probe_name = getattr(ap_meta, "imec_used_probe_name", None) or getattr(ap_meta, "used_probe_name", None) or f"imec{np_num - 1}"
        file_name = getattr(ap_meta, "fileName", "")

    # Try to find in spikeglx_data directory
    sglx_dir = data_root / day / "spikeglx_data"
    # Look for patterns like rec007/rec007_imec0/rec007_t0.imec0.ap.bin
    for rec_dir in sglx_dir.glob(f"*{rec}*"):
        if rec_dir.is_dir():
            for imec_dir in rec_dir.glob(f"*{probe_name}*"):
                if imec_dir.is_dir():
                    for bin_file in imec_dir.glob("*.ap.bin"):
                        return bin_file

    # Fallback: construct path directly
    sglx_rec = f"rec{rec}"
    imec_rec_dir = sglx_dir / sglx_rec / f"{sglx_rec}_{probe_name}"
    bin_name = f"{sglx_rec}_t0.{probe_name}.ap.bin"
    return imec_rec_dir / bin_name


def _find_single_rec_bin(
    cfg: MindSnagConfig, day: str, rec: str, tower: str, np_num: int,
) -> Path:
    """Find the .ap.bin file for a single (non-grouped) recording."""
    data_root = cfg.data_root
    # Try loading AP meta to find path
    ap_meta_file = data_root / day / rec / f"rec{rec}.{tower}.{np_num}.ap_meta.mat"
    if ap_meta_file.exists():
        meta_data = load_mat(ap_meta_file)
        ap_meta = meta_data.get("ap_meta", {})
        return _find_rec_bin(data_root, day, rec, ap_meta, np_num)

    # Fallback: look in spikeglx_data
    sglx_dir = data_root / day / "spikeglx_data"
    for bin_file in sglx_dir.rglob(f"*{rec}*.ap.bin"):
        return bin_file

    raise FileNotFoundError(
        f"Could not find .ap.bin for rec {rec}, day {day}"
    )


def _run_ks4_api(
    input_data: Path,
    results_dir: Path,
    cfg: MindSnagConfig,
) -> None:
    """Run Kilosort4 via the Python API.

    Uses ``kilosort.run_kilosort()`` directly instead of subprocess.
    """
    try:
        from kilosort import run_kilosort
        from kilosort.parameters import DEFAULT_SETTINGS
    except ImportError as e:
        raise ImportError(
            "kilosort package not installed. Install with: pip install 'kilosort>=4.0.20'"
        ) from e

    settings = dict(DEFAULT_SETTINGS)
    settings["data_dir"] = str(input_data.parent)
    settings["results_dir"] = str(results_dir)
    settings["n_chan_bin"] = 385  # default for NP1
    settings["batch_size"] = 60000

    logger.info("Starting Kilosort4...")
    run_kilosort(
        settings=settings,
        filename=str(input_data),
        results_dir=results_dir,
    )
    logger.info("Kilosort4 completed successfully.")
