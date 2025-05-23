from __future__ import annotations

from dataclasses import asdict, dataclass
from multiprocessing.pool import ThreadPool
from pathlib import Path
from typing import Any, Dict, List, Set

import pandas as pd
from matplotlib import pyplot as plt
from s2clientprotocol.sc2api_pb2 import ResponseObservation
from scipy.signal import find_peaks

from sc2_combat_detector.decorators import load_observed_replay
from sc2_combat_detector.function_arguments.file_detect_combat_args import (
    FileDetectCombatArgs,
)
from sc2_combat_detector.function_results.file_detect_combat_result import (
    FileDetectCombatResult,
)
from sc2_combat_detector.proto import observation_collection_pb2 as obs_collection_pb
from sc2_combat_detector.settings import SUFFIX


@dataclass
class PlayerFeatures:
    gameloop: int
    killed_minerals_army: int
    killed_vespene_army: int
    total_damage_dealt: int


def get_relevant_features(player_obs: ResponseObservation) -> PlayerFeatures:
    """
    Selector function that acquires the relevant data from player observation.

    Parameters
    ----------
    player_obs : ResponseObservation
        Response observation as defiend by the s2clientprotocol.

    Returns
    -------
    PlayerFeatures
        Returns player features relevant for further processing.
    """

    gameloop = player_obs.game_loop

    killed_minerals_army = player_obs.score.score_details.killed_minerals.army
    killed_vespene_army = player_obs.score.score_details.killed_vespene.army

    damage_dealt_selector = player_obs.score.score_details.total_damage_dealt

    damage_dealt_life = damage_dealt_selector.life
    damage_dealt_energy = damage_dealt_selector.energy
    damage_dealt_shields = damage_dealt_selector.shields

    total_damage_dealt = damage_dealt_life + damage_dealt_energy + damage_dealt_shields

    player_features = PlayerFeatures(
        gameloop=gameloop,
        killed_minerals_army=killed_minerals_army,
        killed_vespene_army=killed_vespene_army,
        total_damage_dealt=total_damage_dealt,
    )

    return player_features


def add_features_to_dict(
    dict_to_fill: Dict[str, Any],
    feature_dict: Dict[str, Any],
    skip_keys: Set[str],
    prefix: str,
) -> Dict[str, Any]:
    """
    Merges one of the dicts into another, adds a prefix to the previously available
    key to distinguish between players.

    Parameters
    ----------
    dict_to_fill : Dict[str, Any]
        Dictionary which will be filled in with the data.
    feature_dict : Dict[str, Any]
        Dictionary with the features that will be added to the output dictionary with
        a new key prefix.
    skip_keys : Set[str]
        Keys to be skipped when filling out a new dictionary.
    prefix : str
        Prefix to be added for each of the new keys.

    Returns
    -------
    Dict[str, Any]
        Returns the filled out dict with the new prefixed keys.
    """

    for key, value in feature_dict.items():
        if key in skip_keys:
            continue
        dict_to_fill[f"{prefix}_{key}"] = value

    return dict_to_fill


def get_game_features(
    proto_obs: obs_collection_pb.GameObservationCollection,
) -> Dict[str, Dict[str, Any]]:
    """
    Acquires the features selected for combat detection based on selector functions.

    Parameters
    ----------
    proto_obs : obs_collection_pb.GameObservationCollection
        Proto objects containing a collection of all observations within a game.

    Returns
    -------
    Dict[str, Dict[str, Any]]
        Returns a dictionary with the selcted features keyed by the player.

    Raises
    ------
    ValueError
        Raises an error when received observation gameloops for both of the players
        are not identical.
    """

    game_features_dict = dict()

    # Detection will happen for all of the observation intervals.
    # This means that the detection can be ran multiple times on other detection results
    # as long as they come as game observation collections:
    for observation_interval in proto_obs.observation_intervals:
        for observation in observation_interval.observations:
            player1_observation = observation.player1.observation
            player1_features = get_relevant_features(player_obs=player1_observation)

            player2_observation = observation.player2.observation
            player2_features = get_relevant_features(player_obs=player2_observation)

            if player1_features.gameloop != player2_features.gameloop:
                raise ValueError(
                    "Cannot get different gameloop for both player observations!"
                )

            player1_dict = asdict(player1_features)
            player2_dict = asdict(player2_features)

            dict_of_features = {}
            skip_keys = {"gameloop"}
            dict_of_features = add_features_to_dict(
                dict_to_fill=dict_of_features,
                feature_dict=player1_dict,
                skip_keys=skip_keys,
                prefix="player1",
            )

            dict_of_features = add_features_to_dict(
                dict_to_fill=dict_of_features,
                feature_dict=player2_dict,
                skip_keys=skip_keys,
                prefix="player2",
            )

            game_features_dict[player1_features.gameloop] = dict_of_features

    return game_features_dict


def plot_features(
    dataframe: pd.DataFrame,
    vertical_marks: List[obs_collection_pb.ObservationInterval] = [],
    bypass_columns: Set[str] = set("gameloop"),
) -> None:
    print(dataframe.head())

    for col in dataframe.columns:
        if col in bypass_columns:
            continue
        plt.plot(dataframe["gameloop"], dataframe[col], label=col)

    for i, obs_interval in enumerate(vertical_marks):
        start = obs_interval.start_time
        end = obs_interval.end_time

        plt.axvline(
            x=start,
            color="green",
            linestyle="--",
            alpha=0.7,
            label="combat start" if i == 0 else "",
        )
        plt.axvline(
            x=end,
            color="red",
            linestyle="--",
            alpha=0.7,
            label="combat end" if i == 0 else "",
        )

    plt.xlabel("gameloop")
    plt.ylabel("value")
    plt.legend()
    plt.title("Feature values over gameloop")
    plt.show()


def combine_signals(dataframe: pd.DataFrame) -> pd.DataFrame:
    """
    Combines signals picked for combat detection. It does not matter if one or the other
    player started loosing their units as long as it can be called `combat`

    Parameters
    ----------
    dataframe : pd.DataFrame
        Dataframe of all of the features.

    Returns
    -------
    pd.DataFrame
        Dataframe with combined signals for combat detection.
    """

    result_dataframe = dataframe.copy(deep=True)

    result_dataframe["total_resources_killed"] = (
        result_dataframe["player1_killed_minerals_army"].diff(55).fillna(0)
        + result_dataframe["player1_killed_vespene_army"].diff(55).fillna(0)
        + result_dataframe["player2_killed_minerals_army"].diff(55).fillna(0)
        + result_dataframe["player2_killed_vespene_army"].diff(55).fillna(0)
    )

    result_dataframe["total_damage_dealt"] = (
        result_dataframe["player1_total_damage_dealt"]
        + result_dataframe["player2_total_damage_dealt"]
    )

    result_dataframe["damage_delta"] = (
        result_dataframe["total_damage_dealt"].diff(55).fillna(0)
    )

    return result_dataframe


def get_combat_intervals(
    resource_peaks: List[int],
    dataframe: pd.DataFrame,
    damage_start_threshold: int,
    damage_stop_threshold: int,
) -> List[obs_collection_pb.ObservationInterval]:
    """
    Finds the intervals from a list of single peaks.

    Parameters
    ----------
    resource_peaks : List[int]
        List of peaks in the signal defined as the base for combat detection.
    dataframe : pd.DataFrame
        Dataframe holding all of the features for which the combat detection is calculated.
    damage_start_threshold : int
        The minimum signal threshold that needs to be broken upwards to state that the fight started.
    damage_stop_threshold : int
        The minimum signal threshold that needs to be broken downwards to state that the fight stopped.

    Returns
    -------
    List[obs_collection_pb.ObservationInterval]
        Returns a list of ObservationInterval that define intervals of (start_combat, end_combat)
        and an empty list of observations that is supposed to be filled in in the re-simulation.
    """

    fights = []
    for peak_index in resource_peaks:
        # Step 1: Backtrack to when damage starts increasing:
        start_index = peak_index
        while (
            start_index > 0
            and dataframe["damage_delta"].iloc[start_index] > damage_start_threshold
        ):
            start_index -= 1

        # Step 2: Go forward to the point where the damage stops changing significantly:
        end_index = peak_index
        while (
            end_index < len(dataframe) - 1
            and dataframe["damage_delta"].iloc[end_index] > damage_stop_threshold
        ):
            end_index += 1

        start_gameloop = dataframe["gameloop"].iloc[start_index]
        end_gameloop = dataframe["gameloop"].iloc[end_index]

        observation_interval = obs_collection_pb.ObservationInterval(
            start_time=start_gameloop,
            end_time=end_gameloop,
        )

        fights.append(observation_interval)

    return fights


def detect_combat_intervals(
    game_feature_dict: Dict[int, Dict[str, Any]],
    min_peak_height: int = 500,
    min_distance_gameloop: int = 1100,
    damage_start_threshold: int = 100,
    damage_stop_threshold: int = 100,
    plot: bool = False,
) -> List[obs_collection_pb.ObservationInterval]:
    """
    Deals with combining signals and detecting combat.

    Parameters
    ----------
    game_feature_dict : Dict[int, Dict[str, Any]]
        Dictionary from which the dataframe will be created.
    min_peak_height : int
        The minimum height of the peak of the signal change to detect the combat.
    min_distance : int
        The minimum gap in gameloops between peaks that is required to find another combat.
    damage_start_threshold : int
        The minimum signal threshold that needs to be broken upwards to state that the fight started.
    damage_stop_threshold : int
        The minimum signal threshold that needs to be broken downwards to state that the fight stopped.

    Returns
    -------
    List[Tuple[int, int]]
        Returns a list of tuples that define intervals of (start_combat, end_combat).
    """

    dataframe = pd.DataFrame.from_dict(data=game_feature_dict, orient="index")
    dataframe = dataframe.reset_index().rename(columns={"index": "gameloop"})

    combined_dataframe = combine_signals(dataframe=dataframe)

    resource_peaks, _ = find_peaks(
        combined_dataframe["total_resources_killed"],
        height=min_peak_height,
        distance=min_distance_gameloop,
    )

    fight_intervals = get_combat_intervals(
        resource_peaks=resource_peaks,
        dataframe=combined_dataframe,
        damage_start_threshold=damage_start_threshold,
        damage_stop_threshold=damage_stop_threshold,
    )

    if plot:
        plot_features(
            dataframe=combined_dataframe,
            vertical_marks=fight_intervals,
            bypass_columns={
                "gameloop",
                "player1_killed_minerals_army",
                "player1_killed_vespene_army",
                "player2_killed_minerals_army",
                "player2_killed_vespene_army",
            },
        )

    return fight_intervals


def detect_combat(detect_combat_args: FileDetectCombatArgs) -> FileDetectCombatResult:
    """
    Loads file with in-game observations and runs the combat detection algorithm.

    Parameters
    ----------
    detect_combat_args : DetectCombatArgs
        Arguments for combat detection, please refer to the class definition.

    Returns
    -------
    DetectCombatResult
        Returns a type representing the result of combat detection, please refer to this class definition.
    """

    # Load the processed observations:
    proto_obs = load_observed_replay(input_filepath=detect_combat_args.filepath)
    # Detect combat:
    # combat_detector = CombatDetector()
    game_feature_dict = get_game_features(proto_obs=proto_obs)

    combat_intervals = detect_combat_intervals(game_feature_dict=game_feature_dict)

    replay_filepath = Path(proto_obs.replay_path).resolve()
    result = FileDetectCombatResult(
        filepath=detect_combat_args.filepath,
        replay_filepath=replay_filepath,
        combat_intervals=combat_intervals,
    )

    return result


def multithreading_detect_combat(
    input_directory: Path,
    n_threads: int = 12,
) -> List[FileDetectCombatResult]:
    """
    Runs combat detection in multiple threads.

    Parameters
    ----------
    input_directory : Path
        Directory holding observation files.
    n_threads : int
        Number of threads to spawn for combat detection.

    Returns
    -------
    List[DetectCombatResult]
        Returns a list of detected results for further simulation and processing.
        Please refer to the class definition for more information.
    """

    files_to_process = list(input_directory.rglob(f"*{SUFFIX}"))
    if not files_to_process:
        return

    all_detect_combat_args = []
    for file in files_to_process:
        detect_combat_args = FileDetectCombatArgs(filepath=file)
        all_detect_combat_args.append(detect_combat_args)

    with ThreadPool(processes=n_threads) as thread_pool:
        combat_interval_results = thread_pool.map(detect_combat, all_detect_combat_args)

    return combat_interval_results
