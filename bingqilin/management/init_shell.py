from rich import print, print_json

from bingqilin.management import get_app_settings
from bingqilin.management.utils import log_panel

settings = get_app_settings()

log_panel("[blue]Bingqilin app settings loaded![/blue]", level="info", expand=False)
