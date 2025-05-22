from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class ObserveReplayArgs:
    replay_path: Path
    no_skips: bool
    gameloops_to_observe: List[int]
    render: bool = True
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
            feature_screen_size=None,
            feature_minimap_size=None,
            feature_camera_width=24,
            rgb_screen_size="640,480",
            rgb_minimap_size="128",
            no_skips=False,
            gameloops_to_observe=[],
        )

    @staticmethod
    def get_combat_processing_args(
        replay_path: Path,
        gameloops_to_observe: List[int],
    ) -> ObserveReplayArgs:
        return ObserveReplayArgs(
            replay_path=replay_path,
            render=False,
            feature_screen_size=None,
            feature_minimap_size=None,
            feature_camera_width=24,
            rgb_screen_size="640,480",
            rgb_minimap_size="128",
            no_skips=True,
            gameloops_to_observe=gameloops_to_observe,
        )
