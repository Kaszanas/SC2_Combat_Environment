from pathlib import Path

from sc2_combat_detector.settings import SUFFIX
from sc2_combat_detector.decorators import load_observed_replay


def sc2_combat_simulator(combat_detection_dir: Path):
    # Get all of the detected combat files:
    list_of_all_combat_files = list(combat_detection_dir.rglob(f"*{SUFFIX}"))

    # REVIEW: What is the best way to run these?
    # REVIEW: SMACv2 with pysc2_evolved as a dependency instead of the
    # pysc2?
    for combat_interval_file in list_of_all_combat_files:
        # Load the detected combats:
        loaded_combat_file = load_observed_replay(
            input_filepath=combat_interval_file,
        )
        print(loaded_combat_file)
        # Reproduce the combats in the environment:

        # Run the experiments with reinforcement learning or other control algos:
