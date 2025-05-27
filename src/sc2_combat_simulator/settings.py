from pathlib import Path


LOGGING_FORMAT = "[%(asctime)s][%(process)d/%(thread)d][%(levelname)s][%(filename)s:%(lineno)s] - %(message)s"

REPLAY_DIR = Path("./data/agent_replays").resolve()
if not REPLAY_DIR.exists():
    REPLAY_DIR.mkdir(parents=True, exist_ok=True)
