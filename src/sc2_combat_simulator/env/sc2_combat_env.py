import logging
import random
from pysc2_evolved.env.sc2_env import SC2Env

from pysc2_evolved.env.sc2_env import (
    Agent,
    crop_and_deduplicate_names,
    get_default,
)
from s2clientprotocol import sc2api_pb2 as sc_pb

from pysc2_evolved.lib import features

REALTIME_GAME_LOOP_SECONDS = 1 / 22.4
MAX_STEP_COUNT = 524000  # The game fails above 2^19=524288 steps.
NUM_ACTION_DELAY_BUCKETS = 10


class CombatSC2Env(SC2Env):
    def __init__(
        self,
        *,
        map_name=None,
        battle_net_map=False,
        players=None,
        agent_interface_format=None,
        discount=1,
        discount_zero_after_timeout=False,
        visualize=False,
        step_mul=None,
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
    ):
        super().__init__(
            map_name=map_name,
            battle_net_map=battle_net_map,
            players=players,
            agent_interface_format=agent_interface_format,
            discount=discount,
            discount_zero_after_timeout=discount_zero_after_timeout,
            visualize=visualize,
            step_mul=step_mul,
            realtime=realtime,
            save_replay_episodes=save_replay_episodes,
            replay_dir=replay_dir,
            replay_prefix=replay_prefix,
            game_steps_per_episode=game_steps_per_episode,
            score_index=score_index,
            score_multiplier=score_multiplier,
            random_seed=random_seed,
            disable_fog=disable_fog,
            ensure_available_actions=ensure_available_actions,
            version=version,
        )

    # TODO: This needs to be adjusted to recreate the map:
    def _create_join(self):
        """Create the game, and join it."""
        map_inst = random.choice(self._maps)
        self._map_name = map_inst.name

        self._step_mul = max(1, self._default_step_mul or map_inst.step_mul)
        self._score_index = get_default(self._default_score_index, map_inst.score_index)
        self._score_multiplier = get_default(
            self._default_score_multiplier,
            map_inst.score_multiplier,
        )
        self._episode_length = get_default(
            self._default_episode_length,
            map_inst.game_steps_per_episode,
        )
        if self._episode_length <= 0 or self._episode_length > MAX_STEP_COUNT:
            self._episode_length = MAX_STEP_COUNT

        # Create the game. Set the first instance as the host.
        create = sc_pb.RequestCreateGame(
            disable_fog=self._disable_fog,
            realtime=self._realtime,
        )

        if self._battle_net_map:
            create.battlenet_map_name = map_inst.battle_net
        else:
            create.local_map.map_path = map_inst.path
            map_data = map_inst.data(self._run_config)
            if self._num_agents == 1:
                create.local_map.map_data = map_data
            else:
                # Save the maps so they can access it. Don't do it in parallel since SC2
                # doesn't respect tmpdir on windows, which leads to a race condition:
                # https://github.com/Blizzard/s2client-proto/issues/102
                for controller in self._controllers:
                    controller.save_map(map_inst.path, map_data)
        if self._random_seed is not None:
            create.random_seed = self._random_seed
        for p in self._players:
            if isinstance(p, Agent):
                create.player_setup.add(type=sc_pb.Participant)
            else:
                create.player_setup.add(
                    type=sc_pb.Computer,
                    race=random.choice(p.race),
                    difficulty=p.difficulty,
                    ai_build=random.choice(p.build),
                )
        self._controllers[0].create_game(create)

        # Create the join requests.
        agent_players = [p for p in self._players if isinstance(p, Agent)]
        sanitized_names = crop_and_deduplicate_names(p.name for p in agent_players)
        join_reqs = []
        for p, name, interface in zip(
            agent_players, sanitized_names, self._interface_options
        ):
            join = sc_pb.RequestJoinGame(options=interface)
            join.race = random.choice(p.race)
            join.player_name = name
            if self._ports:
                join.shared_port = 0  # unused
                join.server_ports.game_port = self._ports[0]
                join.server_ports.base_port = self._ports[1]
                for i in range(self._num_agents - 1):
                    join.client_ports.add(
                        game_port=self._ports[i * 2 + 2],
                        base_port=self._ports[i * 2 + 3],
                    )
            join_reqs.append(join)

        # Join the game. This must be run in parallel because Join is a blocking
        # call to the game that waits until all clients have joined.
        self._parallel.run(
            (c.join_game, join) for c, join in zip(self._controllers, join_reqs)
        )

        self._game_info = self._parallel.run(c.game_info for c in self._controllers)
        for g, interface in zip(self._game_info, self._interface_options):
            if g.options.render != interface.render:
                logging.warning(
                    "Actual interface options don't match requested options:\n"
                    "Requested:\n%s\n\nActual:\n%s",
                    interface,
                    g.options,
                )

        self._features = [
            features.features_from_game_info(
                game_info=g, agent_interface_format=aif, map_name=self._map_name
            )
            for g, aif in zip(self._game_info, self._interface_formats)
        ]

        self._requested_races = {
            info.player_id: info.race_requested
            for info in self._game_info[0].player_info
            if info.type != sc_pb.Observer
        }
