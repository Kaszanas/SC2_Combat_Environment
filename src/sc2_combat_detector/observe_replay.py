from dataclasses import dataclass
from pathlib import Path
from sc2_combat_detector.proto import observation_collection_pb2 as obs_collection_pb
from sc2_combat_detector.stream_observations import run_observation_stream


@dataclass
class ObserveReplayArgs:
    replay_path: Path
    render: bool = False
    feature_screen_size: int | None = None  # 84,
    feature_minimap_size: int | None = None  # 64,
    feature_camera_width: int = 24
    rgb_screen_size: str = "128,96"
    rgb_minimap_size: str = "16"


def observe_replay(
    observe_replay_args: ObserveReplayArgs,
) -> obs_collection_pb.GameObservationCollection:
    # Open the replay to get replay_data, pass it down and get observations

    # TODO: This should use the proto collectino so that it is easy to dump to files:
    # all_observations = []
    all_observations = obs_collection_pb.GameObservationCollection()
    for observation in run_observation_stream(
        replay_path=observe_replay_args.replay_path,
        render=observe_replay_args.render,
        feature_screen_size=observe_replay_args.feature_screen_size,
        feature_minimap_size=observe_replay_args.feature_minimap_size,
        feature_camera_width=observe_replay_args.feature_camera_width,
        rgb_minimap_size=observe_replay_args.rgb_minimap_size,
        rgb_screen_size=observe_replay_args.rgb_screen_size,
    ):
        all_observations.observations.append(observation)
        # all_observations.append(observation)

    return all_observations
