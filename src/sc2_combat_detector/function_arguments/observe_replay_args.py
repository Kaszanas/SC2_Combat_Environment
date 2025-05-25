from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List


from sc2_combat_detector.function_results.file_detect_combat_result import (
    FileDetectCombatResult,
)
from sc2_combat_detector.proto import observation_collection_pb2 as obs_collection_pb


@dataclass
class ObserveReplayArgs:
    replay_path: Path
    no_skips: bool
    combats_to_observe: FileDetectCombatResult | None
    render: bool = True
    raw: bool = True
    feature_screen_size: int | None = None  # 84,
    feature_minimap_size: int | None = None  # 64,
    feature_camera_width: int = 24
    rgb_screen_size: str = "640,480"
    rgb_minimap_size: str = "16"

    @staticmethod
    def get_initial_processing_args(replay_path: Path) -> ObserveReplayArgs:
        return ObserveReplayArgs(
            replay_path=replay_path,
            render=False,
            raw=False,
            feature_screen_size=None,
            feature_minimap_size=None,
            feature_camera_width=24,
            rgb_screen_size="640,480",
            rgb_minimap_size="128",
            no_skips=False,
            combats_to_observe=None,
        )

    @staticmethod
    def get_combat_processing_args(
        replay_path: Path,
        combats_to_observe: List[obs_collection_pb.ObservationInterval],
    ) -> ObserveReplayArgs:
        return ObserveReplayArgs(
            replay_path=replay_path,
            render=False,
            raw=True,
            feature_screen_size=None,
            feature_minimap_size=None,
            feature_camera_width=24,
            rgb_screen_size="640,480",
            rgb_minimap_size="128",
            no_skips=True,
            combats_to_observe=combats_to_observe,
        )
