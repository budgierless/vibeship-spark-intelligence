import argparse
import json
import random
import time
from pathlib import Path
from typing import Dict, List


def _event(event_type: str, session_id: str, payload: Dict, tool_name: str = None,
           tool_input: Dict = None) -> Dict:
    return {
        "event_type": event_type,
        "session_id": session_id,
        "timestamp": time.time(),
        "data": {"payload": payload},
        "tool_name": tool_name,
        "tool_input": tool_input or {},
        "error": None,
    }


def _vibecoding_events(n: int) -> List[Dict]:
    out: List[Dict] = []
    for i in range(n):
        repo = "spark-core"
        commit_id = f"c{i:04d}"
        out.append(
            _event(
                "post_tool",
                "bench-vibe",
                {"text": f"commit {commit_id} refactor repo={repo}"},
                tool_name="Write",
                tool_input={"repo": repo, "commit_id": commit_id, "files_changed": 3},
            )
        )
        out.append(
            _event(
                "post_tool",
                "bench-vibe",
                {"text": "ci failed test_name=test_login error_code=AssertionError"},
                tool_name="Bash",
                tool_input={"repo": repo, "test_name": "test_login", "error_code": "AssertionError"},
            )
        )
        out.append(
            _event(
                "post_tool",
                "bench-vibe",
                {"text": "deploy success env=prod"},
                tool_name="Bash",
                tool_input={"repo": repo, "env": "prod", "status": "success"},
            )
        )
    return out


def _game_dev_events(n: int) -> List[Dict]:
    out: List[Dict] = []
    for i in range(n):
        playtest_id = f"pt{i:04d}"
        rating = random.choice([2, 3, 4, 5])
        out.append(
            _event(
                "user_prompt",
                "bench-game",
                {"text": f"playtest feedback playtest_id={playtest_id} rating={rating} fun"},
            )
        )
        out.append(
            _event(
                "post_tool",
                "bench-game",
                {"text": "balance change system=combat change=reduce enemy hp"},
                tool_name="Edit",
                tool_input={"system": "combat", "change": "reduce enemy hp"},
            )
        )
        out.append(
            _event(
                "post_tool",
                "bench-game",
                {"text": "retention metric metric_name=D1 metric_value=0.35"},
                tool_name="Bash",
                tool_input={"metric_name": "D1", "metric_value": 0.35},
            )
        )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic events for chip benchmarks.")
    parser.add_argument("--out", default=str(Path("benchmarks") / "synthetic_events.jsonl"))
    parser.add_argument("--vibe", type=int, default=50, help="Number of vibecoding bundles")
    parser.add_argument("--game", type=int, default=50, help="Number of game dev bundles")
    args = parser.parse_args()

    events = []
    events.extend(_vibecoding_events(args.vibe))
    events.extend(_game_dev_events(args.game))
    random.shuffle(events)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")

    print(f"[bench] wrote {out_path} ({len(events)} events)")


if __name__ == "__main__":
    main()
