import enum
import logging
from pathlib import Path

import click

from sc2_combat_detector.combat_detector_pipeline import combat_detector_pipeline
from sc2_combat_detector.settings import LOGGING_FORMAT


import matplotlib


class LogLevel(str, enum.Enum):
    """Log levels for the application."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@click.command(
    help="Tool to acquire action observations from the StarCraft 2 replays, and detect combat. Produces intermediate files for sc2_combat_simulator."
)
@click.option(
    "--replaypack_directory",
    type=click.Path(
        dir_okay=True,
        file_okay=False,
        resolve_path=True,
        path_type=Path,
    ),
    required=True,
    help="Path to the directory that contains replaypacks to be processed.",
)
@click.option(
    "--output_directory",
    type=click.Path(
        dir_okay=True,
        file_okay=False,
        resolve_path=True,
        path_type=Path,
    ),
    required=True,
    help="Path to the output directory, the files processed by the game engine will be placed there for seeding the game engine.",
)
@click.option(
    "--combat_output_directory",
    type=click.Path(
        dir_okay=True,
        file_okay=False,
        resolve_path=True,
        path_type=Path,
    ),
    required=True,
    help="Path to the output directory which will hold full observations for the detected combats. This output will be used to re-create the environment for the agents.",
)
@click.option(
    "--observe_combat/--no_observe_combat",
    is_flag=True,
    default=True,
    help="If set, the combat detection will be performed and the combat observations will be saved. If set to no_observe_combat, only the detection will be performed without saving the combat observations.",
)
@click.option(
    "--n_threads",
    type=int,
    default=2,
    help="Number of threads to use for running StarCraft 2 instances in parallel. Default is 4.",
)
@click.option(
    "--debug/--no_debug",
    is_flag=True,
    default=False,
    help="If set, the debug mode will be enabled. This forces the proto messages to be trimmed to only one observation per interval.",
)
@click.option(
    "--log",
    type=click.Choice(list(LogLevel), case_sensitive=False),
    default=LogLevel.WARNING,
    help="Log level. Default is WARNING.",
)
def main(
    replaypack_directory: Path,
    output_directory: Path,
    combat_output_directory: Path,
    observe_combat: bool,
    n_threads: int,
    debug: bool,
    log: LogLevel,
):
    # Run PySC2 parser and then load the data and perform combat detection:
    numeric_level = getattr(logging, log.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {numeric_level}")
    logging.basicConfig(level=logging.INFO, format=LOGGING_FORMAT)

    if not output_directory.exists():
        logging.warning(
            f"Output directory path {str(output_directory)} did not exist! Creating!"
        )
        output_directory.mkdir(parents=True)

    if not combat_output_directory.exists():
        logging.warning(
            f"Combat output directory path {str(combat_output_directory)} did not exist! Creating!"
        )
        combat_output_directory.mkdir(parents=True)

    combat_detector_pipeline(
        replaypack_directory=replaypack_directory,
        output_directory=output_directory,
        combat_output_directory=combat_output_directory,
        observe_combat=observe_combat,
        n_threads=n_threads,
        debug_mode=debug,
    )


if __name__ == "__main__":
    matplotlib.use("Agg")  # Use non-interactive backend for file output

    main()
