from pathlib import Path
from typing import List

from sc2_combat_detector.decorators import load_observed_replay
from sc2_combat_detector.settings import SUFFIX

from sc2_combat_detector.proto import observation_collection_pb2 as obs_collection_pb

from scipy.signal import find_peaks


# TODO: How do I provide a selection mechanism for the proto message?
# I want an interface that can be used for any feature that is found in an observation:
class DetectionFeature:
    def __init__(self, selector, threshold: int | float, diff_step: int):
        self.selector = selector
        self.threshold = threshold
        self.diff_step = diff_step

        # This will be acuumulated:
        self.derivative = []

        # REVIEW: This can be controlled from the outside loop as well.
        # I don't know if this should be here.
        # Used to count between which points to get the derivative:
        self.got_obs = 0

    # TODO: There is a chance that this can be done just with find_peaks:
    #
    def accumulate_derivative(self, observation: obs_collection_pb.Observation):
        # REVIEW: Select the feature and observe the first sample:
        if not self.derivative:
            self.derivative = ["OBSERVATION VALUE"]
            self.got_obs += 1
            return

        # REVIEW: Start accumulating:
        # Got enough steps to calculate another diff:
        if self.got_obs % self.diff_step == 0:
            current_diff = self.derivative[-1] - "OBSERVATION VALUE"
            self.derivative.append(current_diff)
            self.got_obs += 1

    def _apply_threshold(self):
        # REVIEW: How do
        detected_peaks = find_peaks(threshold=self.threshold)

        return detected_peaks

    def get_detected_intervals(self) -> List[obs_collection_pb.Observation]:
        detected_intervals = self._apply_threshold()

        return detected_intervals


class CombatDetector:
    def __init__(self, observations, features: List[DetectionFeature]):
        self.observations = observations

        # TODO: This needs to provide a way to select which values we want to
        # use to do the detection:
        self.features = features

    # TODO: Run first derivative on all of the features below.
    # TODO: Detect peaks.
    # TODO: Does a combination of these features need to meet a threshold?
    # TODO: Or is it safe for just one of them to be triggered?
    def accumulate_derivative(self, observation) -> None:
        #   // Sum of minerals and vespene of units, belonging to the opponent, that the player has destroyed.
        #   optional float killed_value_units = 5;

        #   // Sum of enemies catagories destroyed in minerals.
        #   optional CategoryScoreDetails killed_minerals = 14;
        #   // Sum of enemies catagories destroyed in vespene.
        #   optional CategoryScoreDetails killed_vespene = 15;

        #   //  Sum of lost minerals for the player in each category.
        #   optional CategoryScoreDetails lost_minerals = 16;
        #   // Sum of lost vespene for the player in each category.
        #   optional CategoryScoreDetails lost_vespene = 17;

        #   // Sum of damage dealt to the player's opponent for each category.
        #   optional VitalScoreDetails total_damage_dealt = 24;
        #   // Sum of damage taken by the player for each category.
        #   optional VitalScoreDetails total_damage_taken = 25;

        # Average fight can be about 1000 ~ 1250 minerals on both sides
        # Duration of a fight can be between 10s and 25s

        for feature in self.features:
            feature.accumulate_derivative()

        pass

    # TODO: This should return a list of observations from the start time
    # to the end time of the combat, from these observations the environment will be
    # seeded:
    def get_detected_intervals(self) -> List[List[obs_collection_pb.Observation]]:
        # Return a list of lists, each of the detected combats needs to have a start observation
        # and a stop observation. (start_time, end_time)

        # REVIEW: This is naive, I need to have a better mechanism where I can
        # REVIEW: merge these intervals, this seems like a CS LeetCode type thingy.
        # REVIEW: If I return all intervals without merging them, there will simply be
        # REVIEW: more of them for the same timesteps in some cases:
        all_detected_intervals = []
        for feature in self.features:
            detected_feature_intervals = feature.get_detected_intervals()
            all_detected_intervals.append(detected_feature_intervals)

        merged_detected_intervals = self._merge_intervals(
            all_detected_intervals=all_detected_intervals
        )

        return merged_detected_intervals

    @staticmethod
    def _merge_intervals(
        all_detected_intervals,
    ) -> List[List[obs_collection_pb.Observation]]:
        pass


# TODO: This can return the proto messages and these can be saved to drive too:
def detect_combat(input_directory: Path):
    # TODO: Load all of the pre-processed replays and start detecting combat:

    files_to_process = list(input_directory.rglob(f"*{SUFFIX}"))
    if not files_to_process:
        return

    all_combats = []
    for file in files_to_process:
        # Load the processed observations:
        proto_obs = load_observed_replay(input_filepath=file)
        # Detect combat:
        combat_detector = CombatDetector()
        for observation in proto_obs.observations:
            combat_detector.accumulate_derivative(observation=observation)

        detected_combats = combat_detector.get_detected_intervals()
        all_combats.append(detected_combats)
