import enum
import logging
from pathlib import Path
import click

from sc2_combat_simulator.combat_simulator import sc2_combat_simulator
from sc2_combat_simulator.settings import LOGGING_FORMAT


class LogLevel(str, enum.Enum):
    """Log levels for the application."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@click.command(
    help="Runs combat simulations with agents. Leverages the output from sc2_combat_detector."
)
@click.option(
    "--combat_detection_dir",
    type=click.Path(
        dir_okay=True,
        file_okay=False,
        resolve_path=True,
        path_type=Path,
    ),
    required=True,
    help="",
)
@click.option(
    "--log",
    type=click.Choice(list(LogLevel), case_sensitive=False),
    default=LogLevel.WARNING,
    help="Log level. Default is WARNING.",
)
def main(
    combat_detection_dir: Path,
    log: LogLevel,
):
    numeric_level = getattr(logging, log.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {numeric_level}")
    logging.basicConfig(level=logging.INFO, format=LOGGING_FORMAT)

    sc2_combat_simulator(combat_detection_dir=combat_detection_dir)


if __name__ == "__main__":
    main()
