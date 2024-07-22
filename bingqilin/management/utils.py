from typing import Literal

import rich
from rich.panel import Panel

LOG_PANEL_STYLES = {"info": "blue", "warning": "yellow", "error": "red"}


def log_panel(
    text, level: Literal["info", "warning", "error"] = "error", expand: bool = True
):
    """
    Convenience function for rich printing a panel to display an error.
    """
    panel_style = LOG_PANEL_STYLES[level]
    rich.print(
        Panel(
            text,
            title=level.title(),
            title_align="left",
            style=panel_style,
            expand=expand,
        )
    )
