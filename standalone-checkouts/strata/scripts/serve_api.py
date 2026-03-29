"""Serve the STRATA FastAPI app with uvicorn."""

from __future__ import annotations


def main() -> None:
    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit("Install API extras first: pip install -e .[api]") from exc

    uvicorn.run("hetero_conformal.api:create_app", factory=True, host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
