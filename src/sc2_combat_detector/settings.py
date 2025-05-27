from pathlib import Path


LOGGING_FORMAT = "[%(asctime)s][%(process)d/%(thread)d][%(levelname)s][%(filename)s:%(lineno)s] - %(message)s"

# Suffix for cache files, this is used in multiple places:
SUFFIX = ".binpb"

PLOT_DIR = Path("./plots").resolve()
if not PLOT_DIR.exists():
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
