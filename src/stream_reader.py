"""Solo la URL del stream (la misma que pones en el navegador)."""

STREAM_URL = "http://192.168.4.1/streaming"


if __name__ == "__main__":
    import sys
    from pathlib import Path

    _repo_root = Path(__file__).resolve().parent.parent
    if str(_repo_root) not in sys.path:
        sys.path.insert(0, str(_repo_root))
    from src.main import main

    main()
