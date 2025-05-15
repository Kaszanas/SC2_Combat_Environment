import enum
import logging
from pathlib import Path
from typing_extensions import Annotated

import typer

from sc2_combat_detector.combat_detector import combat_detector
from sc2_combat_detector.settings import LOGGING_FORMAT


class LogLevel(str, enum.Enum):
    """Log levels for the application."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


def main(
    replaypack_directory: Annotated[
        Path,
        typer.Option(
            help="Path to the directory that contains replaypacks to be processed.",
            path_type=Path,
            resolve_path=True,
            exists=True,
            file_okay=False,
            dir_okay=True,
        ),
    ],
    output_directory: Annotated[
        Path,
        typer.Option(
            help="Path to the output directory, the files processed by the game engine will be placed there for seeding the game engine.",
            path_type=Path,
            resolve_path=True,
            file_okay=False,
            dir_okay=True,
        ),
    ],
    log: Annotated[
        LogLevel,
        typer.Option(
            help="Set the log level.",
            case_sensitive=False,
        ),
    ] = LogLevel.INFO,
):
    # Run Pysc2 parser and then load the data and perform combat detection:

    numeric_level = getattr(logging, log.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {numeric_level}")
    logging.basicConfig(level=logging.INFO, format=LOGGING_FORMAT)

    if not output_directory.exists():
        logging.warning(
            f"Output directory path {str(output_directory)} did not exist! Creating!"
        )
        output_directory.mkdir(parents=True)

    combat_detector(
        replaypack_directory=replaypack_directory,
        output_directory=output_directory,
    )


if __name__ == "__main__":
    typer.run(main)
