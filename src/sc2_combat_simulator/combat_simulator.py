from pathlib import Path

from typing import List, Set

import s2clientprotocol.raw_pb2 as sc2proto_raw_pb

import sc2_combat_detector.proto.observation_collection_pb2 as obs_collection_pb
from pysc2_evolved.agents.no_op_agent import NoOpAgent
from pysc2_evolved.agents.random_agent import RandomAgent
from pysc2_evolved.env import sc2_env
from pysc2_evolved.env.run_loop import run_loop
from pysc2_evolved.env.sc2_env import Agent, Bot
from sc2_combat_detector.decorators import load_observed_replay
from sc2_combat_detector.settings import SUFFIX
from sc2_combat_simulator.env.sc2_combat_env import CombatSC2Env
from sc2_combat_simulator.function_results.player_units_map_state import (
    PlayerUnitsMapState,
)

# from sc2_combat_simulator.env.sc2_combat_env import CombatSC2Env
from sc2_combat_simulator.register_custom_map import register_custom_map
from sc2_combat_simulator.settings import REPLAY_DIR


def filter_units(
    units: List[sc2proto_raw_pb.Unit],
    unit_types_to_ignore: Set[int] = {},
) -> List[sc2proto_raw_pb.Unit]:
    """
    Filters the units based on several criteria required to recreate the combat scenarios.

    Parameters
    ----------
    units : List[sc2proto_raw_pb.Unit]
        List of all of the observed units.
    unit_types_to_ignore : Set[int], optional
        Types of units that should be ignored, by default {}

    Returns
    -------
    List[sc2proto_raw_pb.Unit]
        Returns a list of filtered units that are supposed to be placed on the map.
    """

    units_to_keep = []
    for unit in units:
        # Filter out units that are currently being built:
        if not unit.is_active:
            continue

        # Filter out units that are harvesters (probe, scv, drone):
        # Unit has no attribute "type"
        # if unit.type in unit_types_to_ignore:
        #     continue

        # Get only units that are marked as "Self"
        if unit.alliance != sc2proto_raw_pb.Alliance.Self:
            continue

        units_to_keep.append(unit)

    return units_to_keep


def get_all_units(
    observation_interval: obs_collection_pb.ObservationInterval,
) -> List[List[PlayerUnitsMapState]]:
    """
    Acquires the units to re-create combat environment from observation interval.

    Parameters
    ----------
    observation_interval : obs_collection_pb.ObservationInterval
        Observation interval containing the observations of the combat.

    Returns
    -------
    List[List[PlayerUnitsMapState]]
        Returns a list of PlayerUnitsMapState objects for each observation in the interval.
    """

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


def sc2_combat_simulator(
    combat_detection_dir: Path,
    replay_dir: Path = REPLAY_DIR,
):
    """
    Recreates the combat scenarios in SC2 environment based on the detected combats.

    Parameters
    ----------
    combat_detection_dir : Path
        Directory where the message binary files from the detected combats are stored.
    replay_dir : Path, optional
        Directory where the agents' replays will be saved, by default REPLAY_DIR
    """

    # Get all of the detected combat files:
    list_of_all_combat_files = list(combat_detection_dir.rglob(f"*{SUFFIX}"))

    for combat_interval_file in list_of_all_combat_files:
        combat_intervals_observations = load_observed_replay(
            input_filepath=combat_interval_file,
        )

        map_name = combat_intervals_observations.map_hash
        game_version = combat_intervals_observations.game_version

        map_name_prefix = "Map"
        directory = "CombatSimulator"
        map_class_name, _ = register_custom_map(
            map_name=map_name,
            map_name_prefix=map_name_prefix,
            directory=directory,
        )

        for interval in combat_intervals_observations.observation_intervals:
            player_units_map_state = get_all_units(observation_interval=interval)
            only_first_interval_state = player_units_map_state[0]

            players = [RandomAgent(), Bot(race="protoss", difficulty="easy")]

            players = [
                Agent(race=sc2_env.Race["protoss"], name="NoOpAgent"),
                Bot(
                    race=sc2_env.Race["protoss"],
                    difficulty=sc2_env.Difficulty["easy"],
                    build=sc2_env.BotBuild["random"],
                ),
            ]
            agent_classes = [NoOpAgent]

            # Reproduce the combats in the environment:
            # Run the experiments with reinforcement learning or other control algos:
            with (
                CombatSC2Env(
                    map_name=map_class_name,
                    battle_net_map=False,  # Try to get the map from Battle.net (hopefully from cache).
                    players=players,
                    agent_interface_format=sc2_env.parse_agent_interface_format(
                        feature_screen=84,
                        feature_minimap=64,
                        rgb_screen="256",
                        rgb_minimap="128",
                        action_space="raw",
                        use_feature_units=True,
                        use_raw_units=True,
                    ),
                    discount=1.0,
                    discount_zero_after_timeout=False,
                    visualize=False,
                    step_mul=1,
                    realtime=False,
                    save_replay_episodes=0,
                    replay_dir=replay_dir,
                    replay_prefix=None,
                    game_steps_per_episode=0,
                    score_index=-1,
                    score_multiplier=1,
                    random_seed=42,
                    disable_fog=False,
                    ensure_available_actions=True,
                    version=game_version,
                    player_units_map_state=only_first_interval_state,
                ) as env
            ):
                # env = available_actions_printer.AvailableActionsPrinter(env)
                agents = [agent_cls() for agent_cls in agent_classes]
                run_loop(
                    agents=agents,
                    env=env,
                    max_frames=10000,
                    max_episodes=1,
                )
