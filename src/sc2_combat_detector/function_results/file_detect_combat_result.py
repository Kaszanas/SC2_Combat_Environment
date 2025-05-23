from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from sc2_combat_detector.proto import observation_collection_pb2 as obs_collection_pb


@dataclass
class FileDetectCombatResult:
    replay_filepath: Path
    combat_intervals: List[obs_collection_pb.ObservationInterval]
    filepath: Path | None = None

    def get_gameloops_to_observe(self) -> Tuple[List[int], List[int]]:
        """
        Transforms a list of interval tuples into a list of all of the gameloops
        that need to be observed.

        Returns
        -------
        Tuple[List[int], List[int]]
            List of all of the start times, and the gameloops that need to be observed for combat.
        """

        gameloops_to_observe = []
        start_times = []
        for combat_interval in self.combat_intervals:
            combat_start = combat_interval.start_time
            combat_end = combat_interval.end_time

            # Fill in each full step between combat start and combat end:
            full_gameloops = list(range(combat_start, combat_end + 1))
            gameloops_to_observe += full_gameloops
            start_times.append(combat_start)

        return start_times, gameloops_to_observe
