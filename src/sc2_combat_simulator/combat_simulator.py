from dataclasses import dataclass
from pathlib import Path
from typing import List, Set

from sc2_combat_detector.settings import SUFFIX
from sc2_combat_detector.decorators import load_observed_replay

import sc2_combat_detector.proto.observation_collection_pb2 as obs_collection_pb

import s2clientprotocol.raw_pb2 as sc2proto_raw_pb


@dataclass
class EnvSeedData:
    units: List[sc2proto_raw_pb.Unit]


def filter_units(
    units: List[sc2proto_raw_pb.Unit],
    unit_types_to_ignore: Set[int] = {1, 2, 3},
):
    units_to_keep = []
    for unit in units:
        # Filter out units that are currently being built:
        if not unit.is_active:
            continue

        # Filter out units that are harvesters (probe, scv, drone):
        if unit.type in unit_types_to_ignore:
            continue

        # Get only units that are marked as "Self"
        if unit.alliance != sc2proto_raw_pb.Alliance.Self:
            continue

        units_to_keep.append(unit)

    return units_to_keep


def get_all_units(
    observation_interval: obs_collection_pb.ObservationInterval,
):
    units_in_observations = []

    for observation in observation_interval.observations:
        player1_response_obs = observation.player1
        player2_response_obs = observation.player2

        player1_obs = player1_response_obs.observation
        player2_obs = player2_response_obs.observation

        player1_raw_obs = player1_obs.raw_data
        player2_raw_obs = player2_obs.raw_data

        player1_units = player1_raw_obs.units
        player1_map_state = player1_raw_obs.map_state

        player2_units = player2_raw_obs.units
        player2_map_state = player2_raw_obs.map_state

        player1_filtered_units = filter_units(units=player1_units)
        player2_filtered_units = filter_units(units=player2_units)

        print(player1_filtered_units)
        print(player1_map_state)
        print(player2_filtered_units)
        print(player2_map_state)

        units_in_observations.append((player1_filtered_units, player2_filtered_units))

    return units_in_observations


def sc2_combat_simulator(combat_detection_dir: Path):
    # Get all of the detected combat files:
    list_of_all_combat_files = list(combat_detection_dir.rglob(f"*{SUFFIX}"))

    # REVIEW: What is the best way to run these?
    # REVIEW: SMACv2 with pysc2_evolved as a dependency instead of the
    # pysc2?
    for combat_interval_file in list_of_all_combat_files:
        # Load the detected combats:
        combat_intervals_observations = load_observed_replay(
            input_filepath=combat_interval_file,
        )
        print(combat_intervals_observations)
        for interval in combat_intervals_observations.observation_intervals:
            units = get_all_units(observation_interval=interval)
            print(units)
            # Reproduce the combats in the environment:
            # Run the experiments with reinforcement learning or other control algos:
