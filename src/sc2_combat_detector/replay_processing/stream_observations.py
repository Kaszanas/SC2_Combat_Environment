from pathlib import Path
from typing import Any, Callable, Iterable, List, Sequence
from pysc2_evolved.lib.replay import sc2_replay

from pysc2_evolved.lib.replay import sc2_replay_utils
from pysc2_evolved.lib.replay.replay_observation_stream import ReplayObservationStream
from s2clientprotocol import common_pb2
from s2clientprotocol import sc2api_pb2 as sc2api_pb

from pysc2_evolved import run_configs
from sc2_combat_detector.proto import observation_collection_pb2 as obs_collection_pb

import collections


# TODO: Get the type of actions function argument:
def _unconverted_observation(
    observation: sc2api_pb.ResponseObservation,
    actions,
) -> obs_collection_pb.Observation:
    """
    Initializes an unconverted observation for further processing.

    Parameters
    ----------
    observation : sc2api_pb.ResponseObservation
        Original response observation as returned from replay observation stream.
    actions : _type_
        List of actions to issue the requests for.

    Returns
    -------
    obs_collection_pb.Observation
        Returns an observation for further processing.
    """

    player1_obs = observation[0]
    player2_obs = observation[1]

    if player1_obs.observation.game_loop != player2_obs.observation.game_loop:
        raise ValueError("Got desynchronized observations! Gameloops don't match!")

    force_action = sc2api_pb.RequestAction(actions=actions)
    game_loop = player1_obs.observation.game_loop
    unconverted_observation = obs_collection_pb.Observation(
        game_loop=game_loop,
        player1=player1_obs,
        player2=player2_obs,
        force_action=force_action,
        force_action_delay=0,
    )

    return unconverted_observation


def _convert_observation(
    player_observation: obs_collection_pb.Observation,
    force_action_delay: int,
) -> obs_collection_pb.Observation:
    """
    Converts the original observation into another type if required.

    Parameters
    ----------
    player_observation : obs_collection_pb.Observation
        Original player observation.
    force_action_delay : int
        _description_

    Returns
    -------
    obs_collection_pb.Observation
        Observation with changed type, in case of this function it stays the same.
    """

    converted_observation = obs_collection_pb.Observation(
        game_loop=player_observation.game_loop,
        player1=player_observation.player1,
        player2=player_observation.player2,
        force_action=player_observation.force_action,
        force_action_delay=force_action_delay,
    )

    return converted_observation


# Current step sequence will yield observations right before
# the last camera move in a contiguous sequence of camera moves. Consider
# whether we want to change the observation at which the camera action is being
# reported.
def get_step_sequence(action_skips: Iterable[int]) -> Sequence[int]:
    """
    Generates a sequence of step muls for the replay stream.

    In SC2 we train on observations with actions but actions in replays are
    reported in frames after they were taken. We need a step sequence so we can
    advance the SC2 environment to the relevant observations before the action was
    taken and then step again with delta=1 to get the actual action on the next
    frame. A step sequence is key from a performance point of view since at the
    steps where no actions were taken we do not really need to render which is the
    expensive part of processing a replay. We can advance the simulation without
    rendering at a relatively low cost.

    An example stream looks like this:
    (obs_{0},)------(obs_{k-1},)---(obs_{k}, a_{k-1})---(obs_{k+1}, a_{k})...

    The first observation where an action was taken is `obs_{k-1}`, but the replay
    will not report the action until we request the next observation `obs_{k}`.
    In the above case we also have an action taken at timestep k, but it will be
    reported when we request `obs_{k+1}`. A step sequence would allow us to
    get a union of the observations that we want to report for training and
    those that have actions in them. An example step sequence for the above stream
    would be `[k-1, 1, 1]` where we first step k-1 times to get to the first
    observation where an action was taken, then step once to get the actual action
    as it is reported late.

    Args:
      action_skips: A sequence of game loops where actions were taken in the
        replay. This contains the game loops of the observations that happened
        before the action was reported by the replay to align it with the time
        step when the player took the action (replays report past actions). Note
        that the provided action skips sequence is assumed to have already been
        processed to include only relevant frames depending on the action types of
        interest (e.g., with or without camera moves).

    Returns:
      A sequence of step_muls to use in the replay stream.
    """
    prev_game_loop = 0
    steps = []
    for current_game_loop in action_skips:
        if prev_game_loop == 0:
            steps.append(current_game_loop)
        elif current_game_loop - prev_game_loop > 1:
            # We need to yield twice: to get the observation immediately before the
            # action (this is the game loop number we stored in the index), and to
            # get the replay observation that will return the actual actions. This
            # is needed because replays return actions that humans have taken on
            # previous frames.
            steps.append(1)
            steps.append(current_game_loop - prev_game_loop - 1)
        elif current_game_loop - prev_game_loop == 1:
            # Both previous and current observations had actions, step 1.
            steps.append(1)
        prev_game_loop = current_game_loop
    return steps


def game_interface_setup(
    render: bool,
    feature_screen_size: int | None,
    feature_minimap_size: int | None,
    feature_camera_width: int,
    rgb_screen_size: str,
    rgb_minimap_size: str,
) -> sc2api_pb.InterfaceOptions:
    """
    Function initializing the visual game interface settings to run along with the
    replay observations.

    Parameters
    ----------
    render : bool
        _description_
    feature_screen_size : int | None
        _description_
    feature_minimap_size : int | None
        _description_
    feature_camera_width : int
        _description_
    rgb_screen_size : str
        _description_
    rgb_minimap_size : str
        _description_

    Returns
    -------
    sc2api_pb.InterfaceOptions
        Returns the message type of the sc2api proto required for interface setup.
    """

    interface = sc2api_pb.InterfaceOptions()
    interface.raw = render
    interface.raw_affects_selection = True
    interface.raw_crop_to_playable_area = True
    interface.score = True
    interface.show_cloaked = True
    interface.show_burrowed_shadows = True
    interface.show_placeholders = True
    if feature_screen_size and feature_minimap_size:
        interface.feature_layer.width = feature_camera_width
        interface.feature_layer.resolution.CopyFrom(
            common_pb2.Size2DI(x=feature_screen_size, y=feature_screen_size)
        )
        interface.feature_layer.minimap_resolution.CopyFrom(
            common_pb2.Size2DI(x=feature_minimap_size, y=feature_minimap_size)
        )
        interface.feature_layer.crop_to_playable_area = True
        interface.feature_layer.allow_cheating_layers = True
    if render and rgb_screen_size and rgb_minimap_size:
        rgb_screen_size_split = rgb_screen_size.split(",")
        screen_size_x = int(rgb_screen_size_split[0])
        screen_size_y = int(rgb_screen_size_split[1])

        interface.render.resolution.CopyFrom(
            common_pb2.Size2DI(
                x=screen_size_x,
                y=screen_size_y,
            )
        )
        interface.render.minimap_resolution.CopyFrom(
            common_pb2.Size2DI(
                x=int(rgb_minimap_size),
                y=int(rgb_minimap_size),
            )
        )
    return interface


def run_observation_stream(
    replay_path: Path,
    render: bool,
    feature_screen_size: int | None,  # 84,
    feature_minimap_size: int | None,  # 64,
    feature_camera_width: int,
    rgb_screen_size: str,
    rgb_minimap_size: str,
    no_skips: bool,
    gameloops_to_observe: List[int],
):
    interface = game_interface_setup(
        render=render,
        feature_screen_size=feature_screen_size,
        feature_minimap_size=feature_minimap_size,
        feature_camera_width=feature_camera_width,
        rgb_screen_size=rgb_screen_size,
        rgb_minimap_size=rgb_minimap_size,
    )

    run_config = run_configs.get()
    replay_data = run_config.replay_data(replay_path=str(replay_path))

    # Read the replay first to get the player IDs before the game engine
    # is initiated, this will save some time later:
    replay_file = sc2_replay.SC2Replay(replay_data=replay_data)
    # Read the player IDs first so the replay can be started from some perspective:
    user_id_to_player_info = sc2_replay_utils.get_active_players(replay=replay_file)
    player_id_to_player_info = sc2_replay_utils.get_player_ids(
        user_id_to_object_mapping=user_id_to_player_info
    )
    player_ids: List[int] = list(player_id_to_player_info.keys())
    if len(player_ids) != 2:
        raise ValueError("We only support replays with two active players!")
    player_one_id = player_ids[0]
    player_two_id = player_ids[1]

    with ReplayObservationStream(
        interface_options=interface,
        step_mul=1,
        disable_fog=True,
        add_opponent_observations=True,
    ) as replay_observation_stream:
        # This decides if the observations should only be acquired for
        # when the players make their actions:
        def _accept_step_fn(step):
            return True

        accept_step_function = _accept_step_fn

        step_sequence = None
        if gameloops_to_observe:
            step_sequence = get_step_sequence(action_skips=gameloops_to_observe)

            def _accept_step_fn(step):
                return step in gameloops_to_observe

            accept_step_function = _accept_step_fn

        if not no_skips:
            # Get the loops to which the controller should skip to get only the
            # relevant observations around the player making actions:
            action_skips = sc2_replay_utils.raw_action_skips(replay=replay_file)
            player_action_skips = action_skips[player_one_id]
            step_sequence = get_step_sequence(action_skips=player_action_skips)

            def _accept_step_fn(step):
                return step in player_action_skips

            accept_step_function = _accept_step_fn

        # Start replay at the end. Everyth
        replay_observation_stream.start_replay_from_data(
            replay_data=replay_data,
            player_id=player_one_id,
            opponent_id=player_two_id,
        )
        observations_iterator = replay_observation_stream.observations(
            step_sequence=step_sequence
        )

        yield from observation_consumer(
            observations_iterator=observations_iterator,
            accept_step_fn=accept_step_function,
        )


def observation_consumer(
    observations_iterator: Iterable,
    accept_step_fn: Callable[[Any], bool],
):
    """
    Consumes an observation iterator, and yields a converted representation.

    Parameters
    ----------
    observations_iterator : Iterable
        Observations iterator as returned from replay observations stream.
        This can either be one observation, or multiple observations if two players
        are recorded.
    accept_step_fn : Callable[[Any], bool]
        Function deciding if the given step should be accepted and observed.
        Please refer to the example implementations as used in code.

    Yields
    ------
    obs_collection_pb.Observation
        Returns an observation as defined by the proto message.
    """

    current_observation = next(observations_iterator)
    current_step = current_observation[0].observation.game_loop
    assert current_step == 0

    player_obs_queue = collections.deque()

    for next_observation in observations_iterator:
        step = next_observation[0].observation.game_loop

        if step == 0 or (current_step > 0 and not accept_step_fn(step - 1)):
            # Save the observation even if it didn't have any actions. The step
            # stream also yields the observations immediately before the actions
            # are reported to capture the time the player actually issued the
            # action. If actions were reported at time steps t1 and t2
            # subsequently, we need to yield observation at step t2-1 instead of
            # t1 (this is also what is recorded in the action skips dataset).
            current_observation = next_observation
            continue

        actions = next_observation[0].actions
        unconverted_observation = _unconverted_observation(
            observation=current_observation,
            actions=actions,
        )
        player_obs_queue.append(unconverted_observation)

        while len(player_obs_queue) >= 2:
            # We have saved at least 2 observations in the queue, we can now
            # correctly calculate the true action delay.
            player_obs = player_obs_queue.popleft()
            player_obs_next = player_obs_queue[0]

            force_action_delay = (
                player_obs_next.player1.observation.game_loop
                - player_obs.player1.observation.game_loop
            )

            player_obs.force_action_delay = force_action_delay

            yield player_obs

        current_step = step
        current_observation = next_observation

        # Always use last observation, it contains the player result.
        actions = current_observation[0].actions
        unconverted_observation = _unconverted_observation(
            observation=current_observation,
            actions=actions,
        )
        player_obs_queue.append(unconverted_observation)

    previous_delay = 1
    while player_obs_queue:
        player_obs = player_obs_queue.popleft()
        if len(player_obs_queue) >= 1:
            player_obs_next = player_obs_queue[0]
            force_action_delay = (
                player_obs_next.player1.observation.game_loop
                - player_obs.player1.observation.game_loop
            )
        else:
            # Use previous force action delay, this is only done in the last step.
            # Preserve for reproducibility. In theory the actual delay value
            # shouldn't matter if we retrain checkpoints, since the actions from
            # the last step are never taken.
            force_action_delay = previous_delay

        converted_observation = _convert_observation(
            player_observation=player_obs,
            force_action_delay=force_action_delay,
        )
        previous_delay = force_action_delay

        yield converted_observation
