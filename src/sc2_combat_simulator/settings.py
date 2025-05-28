from pathlib import Path
from typing import Set

from pysc2_evolved.maps.lib import Map


LOGGING_FORMAT = "[%(asctime)s][%(process)d/%(thread)d][%(levelname)s][%(filename)s:%(lineno)s] - %(message)s"

REPLAY_DIR = Path("./data/agent_replays").resolve()
if not REPLAY_DIR.exists():
    REPLAY_DIR.mkdir(parents=True, exist_ok=True)

# REVIEW: Is there a better way of doing this?
# REVIEW: Unfortunately pysc2_evolved relies on finding registered subclasses of Map to work.
# This will be filled dynamically when running the combat_simulator.
# Map class instances are created as needed when loading the combat detection data.
MAPS: Set[Map] = {}
