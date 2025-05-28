from pysc2_evolved.lib.features import AgentInterfaceFormat
from pysc2_evolved.agents.random_agent import RandomAgent
from sc2_combat_simulator.env.sc2_combat_env import Bot, CombatSC2Env
from sc2_combat_simulator.function_results.player_units_map_state import (
    PlayerUnitsMapState,
)
from sc2_combat_simulator.register_custom_map import register_custom_map


if __name__ == "__main__":
    map_name = "1aa58daef01201084db1a993d50704b80b7c2599e7d951b705028d2ae5cd2a5f"
    replay_dir = ""
    game_version = "5.0.14"

    empty_units = PlayerUnitsMapState(
        player1_units=[],
        player2_units=[],
        player1_map_state=None,
        player2_map_state=None,
    )

    prefixed_map_name = f"Map{map_name}"

    custom_map = register_custom_map(
        map_name=map_name,
        directory="CombatSimulator",
        map_name_prefix="Map",
        filename=map_name,
        battle_net=False,
    )
    globals()[prefixed_map_name] = custom_map

    players = [
        # Agent(race="protoss", name="RandomAgent"),
        RandomAgent(),
        Bot(race="protoss", difficulty="easy"),
    ]

    # Add agent interface format:
    CombatSC2Env(
        map_name=prefixed_map_name,
        battle_net_map=False,  # Try to get the map from Battle.net (hopefully from cache).
        players=players,
        agent_interface_format=AgentInterfaceFormat,
        discount=1.0,
        discount_zero_after_timeout=False,
        visualize=False,
        step_mul=1,
        realtime=False,
        save_replay_episodes=0,
        replay_dir=replay_dir,
        replay_prefix=None,
        game_steps_per_episode=None,
        score_index=None,
        score_multiplier=None,
        random_seed=None,
        disable_fog=False,
        ensure_available_actions=True,
        version=game_version,
        player_units_map_state=empty_units,
    )
