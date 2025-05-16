from pathlib import Path
from typing import List

# from pysc2_evolved.bin.replay_actions import replay_actions


from pysc2_evolved import run_configs
# from pysc2_evolved.run_configs import lib as run_configs

from sc2_combat_detector.stream_observations import run_observation_stream

from sc2_combat_detector.proto import observation_collection_pb2 as obs_collection_pb


SUFFIX = ".txtpb"


def observe_replay(replay_path: Path):
    # Open the replay to get replay_data, pass it down and get observations

    run_config = run_configs.get()

    replay_data = run_config.replay_data(replay_path=str(replay_path))

    # TODO: This should use the proto collectino so that it is easy to dump to files:
    all_observations = []
    # all_observations = obs_collection_pb.GameObservationCollection()
    for observation in run_observation_stream(replay_data=replay_data):
        all_observations.append(observation)

    return all_observations


def save_observed_replay(
    replay_observations: List[obs_collection_pb.Observation],
    replay_stem: str,
    output_directory: Path,
    suffix: str = SUFFIX,
) -> Path:
    output_filepath = (
        (output_directory / replay_stem).with_suffix(suffix=suffix).resolve()
    )
    output_filepath_len = (
        (output_directory / replay_stem).with_suffix(suffix=".len").resolve()
    )

    # observations_string = replay_observations.SerializeToString()
    with output_filepath_len.open("w") as flen:
        with output_filepath.open("wb") as fobs:
            for observation in replay_observations:
                # Write lenght of the object in bytes:

                observation_string = observation.SerializeToString()
                observation_byte_len = len(observation_string)
                flen.write(str(observation_byte_len))
                flen.write("\n")

                # Serialize and write to file containing the data:
                fobs.write(observation_string)

    return output_filepath


def load_observed_replay(
    output_directory: Path,
    replay_stem: str,
    suffix: str = SUFFIX,
) -> obs_collection_pb.GameObservationCollection:
    data_files = list(output_directory.rglob(f"{replay_stem}{suffix}"))
    len_files = list(output_directory.rglob(f"{replay_stem}.len"))

    # File cannot be loaded, it was not processed, or the directory is incorrect:
    if not data_files or len_files:
        return

    # There can only be one!
    datafile_to_load = data_files[0]

    # Read lengths of the saved structures:
    pb_len_file = len_files[0]
    lens = None
    with pb_len_file.open("rb") as lens_f:
        lens = lens_f.readlines()

    if not lens:
        return

    observations = []
    with datafile_to_load.open("rb") as f:
        for length in lens:
            single_observation = obs_collection_pb.Observation()
            string_repr = f.read(int(length))
            single_observation.ReadFromString(string_repr)
            observations.append(single_observation)

    return observations


def observe_replays_subfolders(replaypack_directory: Path, output_directory: Path):
    # Run over all subfolders, parse all of the replays.
    # Save the dataset.

    # Get all directories:
    directories_to_parse: List[Path] = []
    for maybe_dir in replaypack_directory.iterdir():
        if maybe_dir.is_dir():
            contains_replays = list(maybe_dir.rglob("*.SC2Replay"))
            if not contains_replays:
                continue

            directories_to_parse.append(maybe_dir)

    # REVIEW: Instead of saving to drive this could run the
    # REVIEW: combat detection immediately!
    # REVIEW: The only issue is that re-running replay simulations is very costly!
    # REVIEW: It takes a very long time to get through the entire game. It's best to do such
    # things offline (After saving all of the relevant data to drive).
    for directory in directories_to_parse:
        list_of_replays = list(directory.rglob("*.SC2Replay"))
        for replay in list_of_replays:
            replay_observations = observe_replay(replay_path=replay)

            # empty_replay_observations = obs_collection_pb.GameObservationCollection()

            replay_stem = replay.stem
            _ = save_observed_replay(
                replay_observations=replay_observations,
                replay_stem=replay_stem,
                output_directory=output_directory,
            )

            _ = load_observed_replay(
                output_directory=output_directory,
                replay_stem=replay_stem,
            )

    # # Run the parsing agents one per directory, these agents should save the output to be read later:
    # with Pool(processes=1) as pool:
    #     list_of_results = pool.map()
