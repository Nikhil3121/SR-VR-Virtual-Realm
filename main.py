"""SR-VR Virtual Realm — entry point. Run: python main.py"""

import sys
import traceback


def main() -> int:
    try:
        from core.engine import Engine
    except Exception:
        print("[FATAL] Failed to import the engine. Did you install requirements?")
        print("        pip install -r requirements.txt")
        traceback.print_exc()
        return 1

    engine = None
    try:
        engine = Engine()
        engine.run()
        return 0
    except KeyboardInterrupt:
        print("Interrupted.")
        return 0
    except Exception:
        print("[FATAL] Unhandled exception in game loop:")
        traceback.print_exc()
        return 1
    finally:
        if engine is not None:
            try:
                engine.shutdown()
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
