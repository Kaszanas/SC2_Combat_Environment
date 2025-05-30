from pathlib import Path
from sc2_combat_detector.detector.detect_combat import multithreading_detect_combat
from sc2_combat_detector.replay_processing.observe_replays import (
    observe_replays_subfolders,
    re_observe_replay_get_combat_snapshots,
)


def combat_detector_pipeline(
    replaypack_directory: Path,
    output_directory: Path,
    combat_output_directory: Path,
    observe_combat: bool,
    n_threads: int,
    debug_mode: bool,
):
    # The observation function does not return anything just because all of the
    # replay observations for a major dataset won't fit into memory.
    # Instead the drive cache should be read sequentially:
    observe_replays_subfolders(
        replaypack_directory=replaypack_directory,
        output_directory=output_directory,
        n_threads=n_threads,
    )

    # The input directory for combat detector is the output directory for the
    # observation gathering function:
    detected_combats = multithreading_detect_combat(
        input_directory=output_directory,
    )
    if not detected_combats or not observe_combat:
        return

    re_observe_replay_get_combat_snapshots(
        replaypack_directory=replaypack_directory,
        combat_output_directory=combat_output_directory,
        detected_combats=detected_combats,
        debug_mode=debug_mode,
    )
