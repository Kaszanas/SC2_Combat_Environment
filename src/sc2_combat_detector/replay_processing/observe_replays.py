from multiprocessing.pool import ThreadPool
from pathlib import Path
from typing import List

from sc2_combat_detector.decorators import drive_observation_cache
from sc2_combat_detector.detector.detect_combat import DetectCombatResult
from sc2_combat_detector.function_arguments.cache_observe_replay_args import (
    CacheObserveReplayArgs,
)
from sc2_combat_detector.function_arguments.observe_replay_args import ObserveReplayArgs
from sc2_combat_detector.function_arguments.thread_observe_replay_args import (
    ThreadObserveReplayArgs,
)

from sc2_combat_detector.proto import observation_collection_pb2 as obs_collection_pb
from sc2_combat_detector.replay_processing.stream_observations import (
    run_observation_stream,
)


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


def run_replay_observation(
    thread_observe_replay_args: ThreadObserveReplayArgs,
):
    """
    Utility function to issue observin a replay with multiple threads.

    Parameters
    ----------
    observe_replay_args : ObserveReplayArgs
        Arguments required to start replay observation.

    Returns
    -------
    obs_collection_pb.GameObservationCollection
        Collection of observations as specified by the configuration of run_observation_stream()
    """

    cache_observe_replay_args = thread_observe_replay_args.cache_processing_args
    observe_replay_args = thread_observe_replay_args.observe_replay_args

    # Issuing decorator here instead of on the function definition:
    cached_observe_replay = drive_observation_cache(
        force=cache_observe_replay_args.force_processing
    )(observe_replay)

    # Running the observations with cache:
    # This function will not returned the observations.
    # There is a high chance that all of the observations from say 20k files
    # will not fit into memory at once. Therefore the drive cache will have to
    # be read sequentially anyway in the further processing steps:
    _ = cached_observe_replay(
        cache_observe_replay_args=cache_observe_replay_args,
        observe_replay_args=observe_replay_args,
    )


def observe_replays_subfolders(
    replaypack_directory: Path,
    output_directory: Path,
    n_processes: int = 6,
    force_processing: bool = False,
):
    """
    Runs replay observation on multiple subdirectories (subfolders). Returns all
    of the collected observations for further processing.
    This function implements a caching mechanism to omit redundant processing.

    Parameters
    ----------
    replaypack_directory : Path
        Directory where StarCraft 2 replaypacks are stored.
    output_directory : Path
        Directory which will contain all of the processed replay observations.
        This directory will follow the same directory structure as the input directory.
    n_processes : int, optional
        Number of threads to spawn for processing, a good starting point
        for simulating with StarCraft 2 game engine is cpu_count / 2.
        Each instance of the game engine should run on at least
        using a single core, by default 6
    force_processing : bool, optional
        Specifies if the algorithm should force the re-processing of replays or
        load the pre-processed results from the cache if available, by default False
    """

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
    args_list = []
    for directory in directories_to_parse:
        list_of_replays = list(directory.rglob("*.SC2Replay"))
        for replay in list_of_replays:
            # Get the arguments required for processing in a multithreading way:
            cache_processing_args = CacheObserveReplayArgs(
                replaypack_directory=replaypack_directory,
                output_directory=output_directory,
                force_processing=force_processing,
            )
            observe_replay_args = ObserveReplayArgs.get_initial_processing_args(
                replay_path=replay
            )
            thread_observe_replay_args = ThreadObserveReplayArgs(
                cache_processing_args=cache_processing_args,
                observe_replay_args=observe_replay_args,
            )

            args_list.append(thread_observe_replay_args)

    # Run the parsing agents one per directory, these agents should save the output to be read later:
    with ThreadPool(processes=n_processes) as pool:
        _ = pool.map(run_replay_observation, args_list)


def get_list_of_combat_gameloops(
    detected_combats: List[DetectCombatResult],
) -> List[int]:
    list_of_gameloops_to_observe = []
    for combat_interval in detected_combats:
        combat_start, combat_end = combat_interval

        # Fill in each full step between combat start and combat end:
        full_gameloops = list(range(combat_start, combat_end + 1))
        list_of_gameloops_to_observe += full_gameloops


# TODO: Implement this:
# TODO: Re-simulate combat with only the requested intervals:
def re_observe_replay_get_combat_snapshots(
    combat_output_directory: Path,
    detected_combats: List[DetectCombatResult],
    force_processing: bool = False,
    n_threads: int = 6,
):
    # TODO: Transform detected combat result into a nested list of gameloops to be observed:

    list_of_gameloops_to_observe = get_list_of_combat_gameloops(
        detected_combats=detected_combats
    )

    all_thread_args = []
    for gameloops_to_observe in list_of_gameloops_to_observe:
        cache_processing_args = CacheObserveReplayArgs(
            replaypack_directory="",
            output_directory=combat_output_directory,
            force_processing=force_processing,
        )

        observe_replay_args = ObserveReplayArgs.get_combat_processing_args(
            replay_path="", gameloops_to_observe=gameloops_to_observe
        )

        thread_args = ThreadObserveReplayArgs(
            cache_processing_args=cache_processing_args,
            observe_replay_args=observe_replay_args,
        )

        all_thread_args.append(thread_args)

    with ThreadPool(processes=n_threads) as thread_pool:
        thread_pool.map(run_replay_observation, all_thread_args)
