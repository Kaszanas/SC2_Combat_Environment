from pysc2_evolved.maps.lib import Map


def register_custom_map(
    map_name: str,
    map_name_prefix: str,
    directory: str = "Melee",
    players: int = 2,
    filename: str | None = None,
    download: str | None = None,
    game_steps_per_episode: int = 16 * 60 * 30,  # 30 minutes at 16 steps per second
    step_mul: int = 8,
    score_index: int = -1,
    score_multiplier: int = 1,
    battle_net: str | None = None,
):
    # Dynamically create a new map class

    class_name = f"{map_name_prefix}{map_name}"

    map_cls = type(
        class_name,
        (Map,),
        {
            "directory": directory,
            "filename": filename or map_name,
            "download": download,
            "game_steps_per_episode": game_steps_per_episode,
            "step_mul": step_mul,
            "score_index": score_index,
            "score_multiplier": score_multiplier,
            "players": players,
            "battle_net": battle_net,
        },
    )

    globals()[class_name] = map_cls

    return class_name, map_cls
