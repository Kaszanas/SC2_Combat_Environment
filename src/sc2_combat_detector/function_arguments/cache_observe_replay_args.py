from dataclasses import dataclass
from pathlib import Path


@dataclass
class CacheObserveReplayArgs:
    replaypack_directory: Path
    output_directory: Path
    force_processing: bool
