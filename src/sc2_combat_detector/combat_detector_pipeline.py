from pathlib import Path
from sc2_combat_detector.detector.detect_combat import detect_combat
from sc2_combat_detector.replay_processing.observe_replays import (
    observe_replays_subfolders,
)


def combat_detector_pipeline(replaypack_directory: Path, output_directory: Path):
    # The observation function does not return anything just because all of the
    # replay observations for a major dataset won't fit into memory.
    # Instead the drive cache should be read sequentially:
    observe_replays_subfolders(
        replaypack_directory=replaypack_directory,
        output_directory=output_directory,
    )

    # The input directory for combat detector is the output directory for the
    # observation gathering function:
    detect_combat(input_directory=output_directory)
