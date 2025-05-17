from pathlib import Path
from typing import List

# from pysc2_evolved.bin.replay_actions import replay_actions


from pysc2_evolved import run_configs
# from pysc2_evolved.run_configs import lib as run_configs

from sc2_combat_detector.decorators import drive_observation_cache
from sc2_combat_detector.stream_observations import run_observation_stream

from sc2_combat_detector.proto import observation_collection_pb2 as obs_collection_pb


def observe_replay(replay_path: Path):
    # Open the replay to get replay_data, pass it down and get observations
    run_config = run_configs.get()
    replay_data = run_config.replay_data(replay_path=str(replay_path))

    # TODO: This should use the proto collectino so that it is easy to dump to files:
    # all_observations = []
    all_observations = obs_collection_pb.GameObservationCollection()
    for observation in run_observation_stream(replay_data=replay_data):
        all_observations.observations.append(observation)
        # all_observations.append(observation)

    return all_observations


def observe_replays_subfolders(
    replaypack_directory: Path,
    output_directory: Path,
):
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
            # Issuing decorator here instead of on the function definition:
            cached_observe_replay = drive_observation_cache(force=False)(observe_replay)
            cached_observe_replay(
                replaypack_directory=replaypack_directory,
                output_directory=output_directory,
                replay_path=replay,
            )

    # # Run the parsing agents one per directory, these agents should save the output to be read later:
    # with Pool(processes=1) as pool:
    #     list_of_results = pool.map()
