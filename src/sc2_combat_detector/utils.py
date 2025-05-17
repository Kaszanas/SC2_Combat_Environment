from __future__ import annotations

from dataclasses import dataclass
from multiprocessing.pool import ThreadPool
from pathlib import Path
from typing import List

from sc2_combat_detector.decorators import drive_observation_cache
from sc2_combat_detector.observe_replay import ObserveReplayArgs, observe_replay

from sc2_combat_detector.proto import observation_collection_pb2 as obs_collection_pb


@dataclass
class CacheObserveReplayArgs:
    replaypack_directory: Path
    output_directory: Path
    force_processing: bool


@dataclass
class ThreadObserveReplayArgs:
    cache_processing_args: CacheObserveReplayArgs
    observe_replay_args: ObserveReplayArgs


def run_replay_observation(
    thread_observe_replay_args: ThreadObserveReplayArgs,
) -> obs_collection_pb.GameObservationCollection:
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
    observations = cached_observe_replay(
        cache_observe_replay_args=cache_observe_replay_args,
        observe_replay_args=observe_replay_args,
    )

    return observations


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
            observe_replay_args = ObserveReplayArgs(replay_path=replay)
            thread_observe_replay_args = ThreadObserveReplayArgs(
                cache_processing_args=cache_processing_args,
                observe_replay_args=observe_replay_args,
            )

            args_list.append(thread_observe_replay_args)

    # Run the parsing agents one per directory, these agents should save the output to be read later:
    with ThreadPool(processes=n_processes) as pool:
        list_of_results: List[obs_collection_pb.GameObservationCollection] = pool.map(
            run_replay_observation, args_list
        )

    return list_of_results
