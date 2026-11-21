"""Launch Beaconfall with the adjacent Keystone checkout."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent


def engine_root(root: Path) -> Path | None:
    """Locate either an exported engine or the adjacent development checkout."""
    for candidate in (root / "vendor", root.parent / "keystone"):
        if (candidate / "keystone" / "__main__.py").is_file():
            return candidate
    return None


def game_spec(arguments: list[str]) -> str:
    """Keep offline tools deterministic; normal windowed play loads records."""
    offline = {"--headless", "--simulate", "--verify-determinism", "--verify-gameplay", "--describe",
               "--validate-project", "--export", "--playtest", "--replay", "--serve", "--new",
               "--version", "--help", "-h", "schema"}
    if any(argument.split("=", 1)[0] in offline for argument in arguments):
        return "beaconfall:Game"
    return "live_game:LiveGame"


def main() -> int:
    arguments = sys.argv[1:]
    if "--verify-gameplay" in arguments:
        from verify_gameplay import main as run_verifier
        return run_verifier(arguments)
    engine = engine_root(ROOT)
    if engine is None:
        print("Why: the Keystone engine was not found next to Beaconfall.\n"
              "Fix: place the keystone and beaconfall project folders side by side, "
              "or restore the exported vendor/keystone folder.", file=sys.stderr)
        return 1
    sys.path.insert(0, str(engine))
    sys.path.insert(0, str(ROOT))
    try:
        from keystone.__main__ import main as run_engine
    except ImportError as exc:
        requirements = ROOT / "requirements.txt" if engine == ROOT / "vendor" else engine / "requirements.txt"
        print(f"Why: Keystone could not load a required dependency ({exc}).\n"
              f"Fix: run python -m pip install -r \"{requirements}\"", file=sys.stderr)
        return 1
    return run_engine(["--game", game_spec(sys.argv[1:]), *sys.argv[1:]])

if __name__ == "__main__":
    raise SystemExit(main())
