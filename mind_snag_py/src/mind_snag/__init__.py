"""mind_snag: Neuropixel spike sorting, curation, and cross-recording neuron stitching."""

__version__ = "2.0.0"

from mind_snag.config import MindSnagConfig
from mind_snag.pipeline import Pipeline

__all__ = ["MindSnagConfig", "Pipeline", "__version__"]
