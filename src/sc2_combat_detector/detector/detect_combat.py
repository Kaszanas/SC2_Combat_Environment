from dataclasses import dataclass, asdict
from multiprocessing.pool import ThreadPool
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from matplotlib import pyplot as plt

from sc2_combat_detector.decorators import load_observed_replay
from sc2_combat_detector.settings import SUFFIX


import pandas as pd


# # TODO: How do I provide a selection mechanism for the proto message?
# # I want an interface that can be used for any feature that is found in an observation:
# class DetectionFeature:
#     def __init__(self, selector, threshold: int | float, diff_step: int):
#         self.selector = selector
#         self.threshold = threshold
#         self.diff_step = diff_step

#         # This will be acuumulated:
#         self.derivative = []

#         # REVIEW: This can be controlled from the outside loop as well.
#         # I don't know if this should be here.
#         # Used to count between which points to get the derivative:
#         self.got_obs = 0

#     # TODO: There is a chance that this can be done just with find_peaks:
#     #
#     def accumulate_derivative(self, observation: obs_collection_pb.Observation):
#         # REVIEW: Select the feature and observe the first sample:
#         if not self.derivative:
#             self.derivative = ["OBSERVATION VALUE"]
#             self.got_obs += 1
#             return

#         # REVIEW: Start accumulating:
#         # Got enough steps to calculate another diff:
#         if self.got_obs % self.diff_step == 0:
#             current_diff = self.derivative[-1] - "OBSERVATION VALUE"
#             self.derivative.append(current_diff)
#             self.got_obs += 1

#     def _apply_threshold(self):
#         # REVIEW: How do
#         detected_peaks = find_peaks(threshold=self.threshold)

#         return detected_peaks

#     def get_detected_intervals(self) -> List[obs_collection_pb.Observation]:
#         detected_intervals = self._apply_threshold()

#         return detected_intervals


# class CombatDetector:
#     def __init__(self, observations, features: List[DetectionFeature]):
#         self.observations = observations

#         # TODO: This needs to provide a way to select which values we want to
#         # use to do the detection:
#         self.features = features

#     # TODO: Run first derivative on all of the features below.
#     # TODO: Detect peaks.
#     # TODO: Does a combination of these features need to meet a threshold?
#     # TODO: Or is it safe for just one of them to be triggered?
#     def accumulate_derivative(self, observation) -> None:
#         #   // Sum of minerals and vespene of units, belonging to the opponent, that the player has destroyed.
#         #   optional float killed_value_units = 5;

#         #   // Sum of enemies catagories destroyed in minerals.
#         #   optional CategoryScoreDetails killed_minerals = 14;
#         #   // Sum of enemies catagories destroyed in vespene.
#         #   optional CategoryScoreDetails killed_vespene = 15;

#         #   //  Sum of lost minerals for the player in each category.
#         #   optional CategoryScoreDetails lost_minerals = 16;
#         #   // Sum of lost vespene for the player in each category.
#         #   optional CategoryScoreDetails lost_vespene = 17;

#         #   // Sum of damage dealt to the player's opponent for each category.
#         #   optional VitalScoreDetails total_damage_dealt = 24;
#         #   // Sum of damage taken by the player for each category.
#         #   optional VitalScoreDetails total_damage_taken = 25;

#         # Average fight can be about 1000 ~ 1250 minerals on both sides
#         # Duration of a fight can be between 10s and 25s

#         for feature in self.features:
#             feature.accumulate_derivative()

#         pass

# TODO: This should return a list of observations from the start time
# to the end time of the combat, from these observations the environment will be
# seeded:
# def get_detected_intervals(self) -> List[List[obs_collection_pb.Observation]]:
#     # Return a list of lists, each of the detected combats needs to have a start observation
#     # and a stop observation. (start_time, end_time)

#     # REVIEW: This is naive, I need to have a better mechanism where I can
#     # REVIEW: merge these intervals, this seems like a CS LeetCode type thingy.
#     # REVIEW: If I return all intervals without merging them, there will simply be
#     # REVIEW: more of them for the same timesteps in some cases:
#     all_detected_intervals = []
#     for feature in self.features:
#         detected_feature_intervals = feature.get_detected_intervals()
#         all_detected_intervals.append(detected_feature_intervals)

#     merged_detected_intervals = self._merge_intervals(
#         all_detected_intervals=all_detected_intervals
#     )

#     return merged_detected_intervals

# @staticmethod
# def _merge_intervals(
#     all_detected_intervals,
# ) -> List[List[obs_collection_pb.Observation]]:
#     pass


@dataclass
class PlayerFeatures:
    gameloop: int
    killed_minerals_army: int
    killed_vespene_army: int
    total_damage_dealt: int


def get_relevant_features(player_obs) -> PlayerFeatures:
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
    suffix: str,
) -> Dict[str, Any]:
    for key, value in feature_dict.items():
        if key in skip_keys:
            continue
        dict_to_fill[f"{suffix}_{key}"] = value

    return dict_to_fill


def get_game_features(proto_obs):
    game_features_dict = dict()
    for observation in proto_obs.observations:
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

        game_features_dict[player1_features.gameloop] = {}

        dict_of_features = {}
        skip_keys = {"gameloop"}
        add_features_to_dict(
            dict_to_fill=dict_of_features,
            feature_dict=player1_dict,
            skip_keys=skip_keys,
            suffix="player1",
        )

        add_features_to_dict(
            dict_to_fill=dict_of_features,
            feature_dict=player2_dict,
            skip_keys=skip_keys,
            suffix="player2",
        )

        game_features_dict[player1_features.gameloop] = dict_of_features

    return game_features_dict


def plot_features():
    pass


def detect_combat_intervals(game_feature_dict: Dict[int, Dict[str, Any]]):
    dataframe = pd.DataFrame.from_dict(data=game_feature_dict, orient="index")
    dataframe = dataframe.reset_index().rename(columns={"index": "gameloop"})

    print(dataframe.head())

    for col in dataframe.columns:
        if col == "gameloop":
            continue
        plt.plot(dataframe["gameloop"], dataframe[col], label=col)

    plt.xlabel("gameloop")
    plt.ylabel("value")
    plt.legend()
    plt.title("Feature values over gameloop")
    plt.show()

    print("something")


@dataclass
class DetectCombatArgs:
    filepath: Path


@dataclass
class DetectCombatResult:
    filepath: Path
    combat_intervals: List[Tuple[int, int]]


def get_combat_intervals(detect_combat_args: DetectCombatArgs):
    # Load the processed observations:
    proto_obs = load_observed_replay(input_filepath=detect_combat_args.filepath)
    # Detect combat:
    # combat_detector = CombatDetector()
    game_feature_dict = get_game_features(proto_obs=proto_obs)

    combat_intervals = detect_combat_intervals(game_feature_dict=game_feature_dict)

    result = DetectCombatResult(
        filepath=detect_combat_args.filepath, combat_intervals=combat_intervals
    )

    return result


# TODO: This can return the proto messages and these can be saved to drive too:
def detect_combat(input_directory: Path, n_threads: int):
    # TODO: Load all of the pre-processed replays and start detecting combat:

    files_to_process = list(input_directory.rglob(f"*{SUFFIX}"))
    if not files_to_process:
        return

    all_detect_combat_args = []
    for file in files_to_process:
        detect_combat_args = DetectCombatArgs(filepath=file)
        all_detect_combat_args.append(detect_combat_args)

    with ThreadPool(processes=n_threads) as thread_pool:
        combat_interval_results = thread_pool.map(
            get_combat_intervals, all_detect_combat_args
        )

    return combat_interval_results
