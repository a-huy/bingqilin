import rich

from bingqilin.management import get_app_settings

settings = get_app_settings()

rich.print("[blue]Bingqilin app settings loaded![/blue]")
