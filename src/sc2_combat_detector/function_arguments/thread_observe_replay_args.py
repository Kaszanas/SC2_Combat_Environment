from dataclasses import dataclass
from sc2_combat_detector.function_arguments.cache_observe_replay_args import (
    CacheObserveReplayArgs,
)
from sc2_combat_detector.function_arguments.observe_replay_args import ObserveReplayArgs


@dataclass
class ThreadObserveReplayArgs:
    cache_processing_args: CacheObserveReplayArgs
    observe_replay_args: ObserveReplayArgs
