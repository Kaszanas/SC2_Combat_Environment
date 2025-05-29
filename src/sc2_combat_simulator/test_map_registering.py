from pysc2_evolved.env import sc2_env, run_loop
from pysc2_evolved.env.sc2_env import Agent
from pysc2_evolved.agents.no_op_agent import NoOpAgent
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
        Agent(race=sc2_env.Race["protoss"], name="NoOpAgent"),
        # RandomAgent(),
        Bot(
            race=sc2_env.Race["protoss"],
            difficulty=sc2_env.Difficulty["easy"],
            build=sc2_env.BotBuild["random"],
        ),
    ]
    agent_classes = [NoOpAgent]

    # Add agent interface format:
    with (
        CombatSC2Env(
            map_name=prefixed_map_name,
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
            player_units_map_state=empty_units,
        ) as env
    ):
        # env = available_actions_printer.AvailableActionsPrinter(env)
        agents = [agent_cls() for agent_cls in agent_classes]
        run_loop.run_loop(agents=agents, env=env, max_frames=10000, max_episodes=1)
        env.save_replay("test_map_registering")
