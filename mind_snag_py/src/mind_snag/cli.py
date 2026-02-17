"""Click CLI for mind_snag: ``mind-snag run ...``

Provides the ``mind-snag`` command with subcommands:
  - ``run``     : Execute the full pipeline
  - ``convert`` : Convert between .mat and HDF5 formats
"""

from __future__ import annotations

import logging
from pathlib import Path

import click


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


@click.group()
@click.version_option(package_name="mind-snag")
def cli() -> None:
    """mind_snag: Neuropixel spike sorting, curation, and neuron stitching."""
    pass


@cli.command()
@click.option("--config", "-c", type=click.Path(exists=True), required=True, help="Path to YAML config file")
@click.option("--day", "-d", required=True, help="Recording date (YYMMDD)")
@click.option("--recs", "-r", required=True, multiple=True, help="Recording numbers (e.g. 007 009 010)")
@click.option("--tower", "-t", required=True, help="Recording setup name")
@click.option("--np", "np_num", type=int, required=True, help="Neuropixel probe number (1 or 2)")
@click.option("--stages", "-s", multiple=True, default=None, help="Stages to run (default: all)")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging")
def run(
    config: str,
    day: str,
    recs: tuple[str, ...],
    tower: str,
    np_num: int,
    stages: tuple[str, ...] | None,
    verbose: bool,
) -> None:
    """Run the spike sorting pipeline."""
    _setup_logging(verbose)

    from mind_snag.config import MindSnagConfig
    from mind_snag.pipeline import Pipeline

    cfg = MindSnagConfig.from_yaml(config)
    pipeline = Pipeline(cfg)

    stage_list = list(stages) if stages else None
    pipeline.run(
        day=day,
        recs=list(recs),
        tower=tower,
        np_num=np_num,
        stages=stage_list,
    )


@cli.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.argument("output_path", type=click.Path())
@click.option("--direction", type=click.Choice(["mat2hdf5", "hdf52mat"]), default="mat2hdf5", help="Conversion direction")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging")
def convert(
    input_path: str,
    output_path: str,
    direction: str,
    verbose: bool,
) -> None:
    """Convert between .mat and HDF5 formats."""
    _setup_logging(verbose)

    from mind_snag.io.converter import convert_file
    convert_file(Path(input_path), Path(output_path), direction)
    click.echo(f"Converted: {input_path} -> {output_path}")


@cli.command()
@click.option("--config", "-c", type=click.Path(exists=True), required=True, help="Path to YAML config file")
@click.option("--day", "-d", required=True, help="Recording date (YYMMDD)")
@click.option("--recs", "-r", required=True, multiple=True, help="Recording numbers")
@click.option("--tower", "-t", required=True, help="Recording setup name")
@click.option("--np", "np_num", type=int, required=True, help="Probe number")
@click.option("--cluster-type", type=click.Choice(["All", "Good", "Isolated"]), default="All")
@click.option("--output-dir", "-o", type=click.Path(), required=True, help="Output directory")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging")
def stitch(
    config: str,
    day: str,
    recs: tuple[str, ...],
    tower: str,
    np_num: int,
    cluster_type: str,
    output_dir: str,
    verbose: bool,
) -> None:
    """Run cross-recording neuron stitching."""
    _setup_logging(verbose)

    from mind_snag.config import MindSnagConfig
    from mind_snag.stitching.stitch_neurons import NeuronStitcher
    from mind_snag.stitching.save_stitch_results import save_stitch_results

    cfg = MindSnagConfig.from_yaml(config)
    grouped = len(recs) > 1

    stitcher = NeuronStitcher(cfg, day, list(recs), tower, np_num, grouped, cluster_type)
    result = stitcher.run()

    out_path = save_stitch_results(cfg, result, output_dir)
    click.echo(f"Stitch results saved: {out_path}")
    click.echo(f"Found {result.stitch_table.shape[0]} stitched neurons")
