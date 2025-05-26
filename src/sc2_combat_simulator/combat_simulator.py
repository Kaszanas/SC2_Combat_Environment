from dataclasses import dataclass
from pathlib import Path
from typing import List, Set

from sc2_combat_detector.settings import SUFFIX
from sc2_combat_detector.decorators import load_observed_replay

import sc2_combat_detector.proto.observation_collection_pb2 as obs_collection_pb

import s2clientprotocol.raw_pb2 as sc2proto_raw_pb

from sc2_combat_simulator.function_results.player_units_map_state import (
    PlayerUnitsMapState,
)


from sc2_combat_simulator.env.sc2_combat_env import CombatSC2Env


@dataclass
class EnvSeedData:
    units: List[sc2proto_raw_pb.Unit]


def filter_units(
    units: List[sc2proto_raw_pb.Unit],
    unit_types_to_ignore: Set[int] = {},
) -> List[sc2proto_raw_pb.Unit]:
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

        get_all_units_result = PlayerUnitsMapState(
            player1_units=player1_filtered_units,
            player2_units=player2_filtered_units,
            player1_map_state=player1_map_state,
            player2_map_state=player2_map_state,
        )

        units_in_observations.append(get_all_units_result)

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
        for interval in combat_intervals_observations.observation_intervals:
            player_units_map_state = get_all_units(observation_interval=interval)
            only_first_interval_state = player_units_map_state[0]
            # Reproduce the combats in the environment:
            # Run the experiments with reinforcement learning or other control algos:
            CombatSC2Env(
                map_name="",
                battle_net_map=True,
                players=None,
                agent_interface_format=None,
                discount=1.0,
                discount_zero_after_timeout=False,
                visualize=False,
                step_mul=1,
                realtime=False,
                save_replay_episodes=0,
                replay_dir=None,
                replay_prefix=None,
                game_steps_per_episode=None,
                score_index=None,
                score_multiplier=None,
                random_seed=None,
                disable_fog=False,
                ensure_available_actions=True,
                version=None,
                player_units_map_state=only_first_interval_state,
            )
