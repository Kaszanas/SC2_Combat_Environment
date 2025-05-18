from dataclasses import dataclass
from pathlib import Path


@dataclass
class ObserveReplayArgs:
    replay_path: Path
    render: bool = False
    feature_screen_size: int | None = None  # 84,
    feature_minimap_size: int | None = None  # 64,
    feature_camera_width: int = 24
    rgb_screen_size: str = "128,96"
    rgb_minimap_size: str = "16"
