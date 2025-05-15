from pathlib import Path
from sc2_combat_detector.utils import observe_replays_subfolders


def combat_detector(replaypack_directory: Path, output_directory: Path):
    observe_replays_subfolders(
        replaypack_directory=replaypack_directory,
        output_directory=output_directory,
    )
