from dataclasses import dataclass


@dataclass
class GetReplayMapHashResult:
    map_hash: str
    game_version: str
