from pathlib import Path


def run_game_engine():
    pass


def parse_subfolders(replaypack_directory: Path):
    # Run over all subfolders, parse all of the replays.
    # Save the dataset.

    # Get all directories:
    directories_to_parse = []
    for maybe_dir in replaypack_directory.iterdir():
        if maybe_dir.is_dir():
            directories_to_parse.append(maybe_dir)
