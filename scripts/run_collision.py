"""Track vehicles and emit causal experimental collision alerts with evidence."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.video_pipeline import arguments, run

if __name__ == '__main__':
    args = arguments('collision analysis').parse_args()
    args.collision = True
    try:
        print(run(args,tracking=True),flush=True)
    except (OSError,RuntimeError,ValueError) as exc:
        raise SystemExit(str(exc))
