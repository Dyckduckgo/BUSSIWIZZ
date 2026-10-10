"""
UI Package for Bussiwzz.
"""

def __getattr__(name: str):
    if name in ("main", "launch_ui"):
        from .app import main, launch_ui
        globals()["main"] = main
        globals()["launch_ui"] = launch_ui
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["main", "launch_ui"]

