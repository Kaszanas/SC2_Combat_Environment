import logging
from multiprocessing.pool import ThreadPool
from pathlib import Path
from typing import List

from sc2_combat_detector.decorators import drive_observation_cache
from sc2_combat_detector.detector.detect_combat import FileDetectCombatResult
from sc2_combat_detector.function_arguments.cache_observe_replay_args import (
    CacheObserveReplayArgs,
)
from sc2_combat_detector.function_arguments.observe_replay_args import ObserveReplayArgs
from sc2_combat_detector.function_arguments.thread_observe_replay_args import (
    ThreadObserveReplayArgs,
)

from sc2_combat_detector.function_results.get_replay_map_hash_result import (
    GetReplayMapHashResult,
)
from sc2_combat_detector.proto import observation_collection_pb2 as obs_collection_pb
from sc2_combat_detector.replay_processing.stream_observations import (
    run_observation_stream,
)

import bisect

import sc2reader


def get_replay_map_information(replay_path: Path) -> str:
    # Read replay with sc2reader to get the map hash:

    # NOTE: Cannot use the sc2_replay.Replay from pysc2 because it cannot
    # NOTE: effectively parse the game data. Something is wrong with the encoding.
    replay = sc2reader.load_replay(str(replay_path), load_level=1)
    map_hash = replay.map_hash

    release_string = replay.release_string
    split_release_string = release_string.split(".")
    game_version = ".".join(split_release_string[:3])

    result = GetReplayMapHashResult(
        map_hash=map_hash,
        game_version=game_version,
    )

    return result


def gameloop_within_interval(
    start_time: int,
    end_time: int,
    game_loop: int,
) -> bool:
    """
    Function checking if a gameloop is placed within a given interval.

    Parameters
    ----------
    start_time : int
        Start time of the interval.
    end_time : int
        End time of the interval.
    game_loop : int
        Game loop to check.

    Returns
    -------
    bool
        True if the gameloop is within the interval, False otherwise.
    """

    # This is a special case, end time for an interval can only be -1
    # if it is set initially as the entire game interval.
    # In that case any gameloop is within the interval:
    if end_time == -1:
        return True

    # Typical case requires for the gameloop to be between start time and end time
    # of an interval to let it through:
    if start_time <= game_loop <= end_time:
        return True

    return False


def verify_observation_lengths(
    all_observations: obs_collection_pb.GameObservationCollection,
    gameloops_to_observe: List[int],
) -> None:
    """
    Checks the lengths of requested observations against the number of all of the
    saved observations.

    Parameters
    ----------
    all_observations : obs_collection_pb.GameObservationCollection
        Collection of multiple intervals of observations.
        Can be thought of as a nested list, please refer to the proto definition.
    gameloops_to_observe : List[int]
        List of the requested gameloops to be observed.
    """

    sum_of_lens = 0
    for observation_interval in all_observations.observation_intervals:
        sum_of_lens += len(observation_interval.observations)

    if len(gameloops_to_observe) != sum_of_lens * 2:
        logging.warning(
            f"Something is wrong, requested observations for {len(gameloops_to_observe)} and received {sum_of_lens} observations!"
        )


# REVIEW: This function handles two distinct cases while attempting to acquire
# observations for detected combat intervals and the actions that are required
# prior to the combat detection.
# If this is too messy I might change this later into two separate functions.
# It starts to seem messy.
def observe_replay(
    observe_replay_args: ObserveReplayArgs,
) -> obs_collection_pb.GameObservationCollection:
    """
    Observes a single replay and returns a collection of observations.

    Parameters
    ----------
    observe_replay_args : ObserveReplayArgs
        Arguments to be used for replay observation, please refer to the class definition.

    Returns
    -------
    obs_collection_pb.GameObservationCollection
        Collection os observations as a proto message type.
    """

    # This will return an empty list if there were no registered combats to observe:
    gameloops_to_observe = None
    start_times = None
    if observe_replay_args.combats_to_observe:
        start_times, gameloops_to_observe = (
            observe_replay_args.combats_to_observe.get_gameloops_to_observe()
        )

    map_information = get_replay_map_information(
        replay_path=observe_replay_args.replay_path,
    )
    all_observations = obs_collection_pb.GameObservationCollection()
    all_observations.replay_path = str(observe_replay_args.replay_path)
    all_observations.map_hash = map_information.map_hash
    all_observations.game_version = map_information.game_version

    # Special case, no combat detection is required so the interval spans the entire game:
    entire_game_observation_interval = None
    if not observe_replay_args.combats_to_observe:
        entire_game_observation_interval = obs_collection_pb.ObservationInterval(
            start_time=0,  # start_time for the case of entire game interval is just the first gameloop!
            end_time=-1,  # special case, this is used in gameloop_within_interval function
        )

        # REVIEW: Mutating arguments may not be the best idea here!!!!!!
        # The entire game observation interval needs to be added so that the
        # later bisecting approach can append the observations in the right way:
        observe_replay_args.combats_to_observe = FileDetectCombatResult(
            replay_filepath=observe_replay_args.replay_path,
            combat_intervals=[entire_game_observation_interval],
        )

        start_times = [entire_game_observation_interval.start_time]

    combat_intervals_list = observe_replay_args.combats_to_observe.combat_intervals
    for observation in run_observation_stream(
        replay_path=observe_replay_args.replay_path,
        render=observe_replay_args.render,
        raw=observe_replay_args.raw,
        feature_screen_size=observe_replay_args.feature_screen_size,
        feature_minimap_size=observe_replay_args.feature_minimap_size,
        feature_camera_width=observe_replay_args.feature_camera_width,
        rgb_minimap_size=observe_replay_args.rgb_minimap_size,
        rgb_screen_size=observe_replay_args.rgb_screen_size,
        no_skips=observe_replay_args.no_skips,
        gameloops_to_observe=gameloops_to_observe,
    ):
        obs_gameloop = observation.game_loop
        # Getting the index of the interval via bisect assumes that the
        # intervals list is sorted and non-overlapping:
        index = bisect.bisect_right(start_times, obs_gameloop) - 1
        curr_interval_start_time = combat_intervals_list[index].start_time
        curr_interval_end_time = combat_intervals_list[index].end_time

        # If gameloop of the observation is equal or higher than the start time
        # and the gameloop is less or equal the end time of the interval,
        # you can keep appending the observations to the currently initialized interval.
        if index >= 0 and gameloop_within_interval(
            start_time=curr_interval_start_time,
            end_time=curr_interval_end_time,
            game_loop=obs_gameloop,
        ):
            observation_interval = combat_intervals_list[index]
            observation_interval.observations.append(observation)

    # This is a special case for getting the final gameloop if no combat intervals are requested:
    # TODO fill in the gameloop of interval end:
    if entire_game_observation_interval:
        entire_game_observation_interval.end_time = obs_gameloop

    for filled_combat_interval in combat_intervals_list:
        all_observations.observation_intervals.append(filled_combat_interval)

    # This is only multiplied by two because for one gameloop we get the
    # observations for both of the players:
    # REVIEW: It seems that one observation is missing from the original
    # REVIEW: requested gameloops to observe, this is not a major issue,
    # REVIEW: but rather a weird inconvenience, this ought to be fixed:
    if gameloops_to_observe:
        verify_observation_lengths(
            all_observations=all_observations,
            gameloops_to_observe=gameloops_to_observe,
        )

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

    # Returning arguments because if there are too much observations they
    # won't fit into memory:
    return thread_observe_replay_args


def observe_replays_subfolders(
    replaypack_directory: Path,
    output_directory: Path,
    n_threads: int = 6,
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
    with ThreadPool(processes=n_threads) as pool:
        _ = pool.map(run_replay_observation, args_list)


def re_observe_replay_get_combat_snapshots(
    replaypack_directory: Path,
    combat_output_directory: Path,
    detected_combats: List[FileDetectCombatResult],
    force_processing: bool = False,
    n_threads: int = 6,
):
    """
    Issues re-observation tasks based on the detected interesting intervals.

    Parameters
    ----------
    replaypack_directory : Path
        Directory containing the replaypacks.
    combat_output_directory : Path
        Directory where the output of the fully observed combat snapshots will be stored.
    detected_combats : List[FileDetectCombatResult]
        List of the detection results with fields like file which was used,
        and the list of detected intervals.
    force_processing : bool, optional
        Specifies if the cache should be forced to re-create, by default False
    n_threads : int, optional
        Number of threads to spawn for re-simulation, by default 6
    """

    all_thread_args = []
    for detection_result in detected_combats:
        cache_processing_args = CacheObserveReplayArgs(
            replaypack_directory=replaypack_directory,
            output_directory=combat_output_directory,
            force_processing=force_processing,
        )

        observe_replay_args = ObserveReplayArgs.get_combat_processing_args(
            replay_path=detection_result.replay_filepath,
            combats_to_observe=detection_result,
        )

        thread_args = ThreadObserveReplayArgs(
            cache_processing_args=cache_processing_args,
            observe_replay_args=observe_replay_args,
        )

        all_thread_args.append(thread_args)

    with ThreadPool(processes=n_threads) as thread_pool:
        arguments_used = thread_pool.map(run_replay_observation, all_thread_args)

    return arguments_used
