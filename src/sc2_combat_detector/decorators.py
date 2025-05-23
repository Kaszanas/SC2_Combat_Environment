from pathlib import Path
from sc2_combat_detector.function_arguments.cache_observe_replay_args import (
    CacheObserveReplayArgs,
)
from sc2_combat_detector.function_arguments.observe_replay_args import ObserveReplayArgs
from sc2_combat_detector.proto import observation_collection_pb2 as obs_collection_pb

import logging

from sc2_combat_detector.settings import SUFFIX


def save_observed_replay(
    replay_observations: obs_collection_pb.GameObservationCollection,
    output_filepath: Path,
) -> Path:
    bin_str_obs = replay_observations.SerializeToString()
    with output_filepath.open("wb") as out_f:
        out_f.write(bin_str_obs)

    return output_filepath


def load_observed_replay(
    input_filepath: Path,
) -> obs_collection_pb.GameObservationCollection:
    observations = obs_collection_pb.GameObservationCollection()
    with input_filepath.open("rb") as in_f:
        raw_data = in_f.read()
        observations.ParseFromString(raw_data)

    return observations


def drive_observation_cache(force: bool = False):
    """Caches the return value of a function based on its arguments."""

    def decorator(func):
        def wrapper(
            cache_observe_replay_args: CacheObserveReplayArgs,
            observe_replay_args: ObserveReplayArgs,
            suffix: str = SUFFIX,
            *args,
            **kwargs,
        ):
            # Getting all of the relevant paths, and creating the output directories
            # if needed:

            replay_stem = observe_replay_args.replay_path.stem

            replay_relative_dir_structure = observe_replay_args.replay_path.relative_to(
                cache_observe_replay_args.replaypack_directory
            ).parent
            output_dir_clone_structure = (
                cache_observe_replay_args.output_directory
                / replay_relative_dir_structure
            ).resolve()
            already_processed_observations_file = (
                output_dir_clone_structure / replay_stem
            ).with_suffix(suffix=suffix)

            if already_processed_observations_file.exists() and not force:
                # Load the observations from drive instead of re-simulating the replay
                # with the game engine. This is making the entire process more efficient!
                observations = load_observed_replay(
                    input_filepath=already_processed_observations_file,
                )

                return observations

            if not output_dir_clone_structure.exists():
                logging.info(
                    f"Output observation file directory did not exist, creating: {str(output_dir_clone_structure)}"
                )
                output_dir_clone_structure.mkdir(parents=True)

            # This is kind of a closed interface the wrapper must be used on a function that takes
            # the replay_path, otherwise this breaks.
            observations = func(observe_replay_args=observe_replay_args)

            _ = save_observed_replay(
                replay_observations=observations,
                output_filepath=already_processed_observations_file,
            )

            return observations

        return wrapper

    return decorator
