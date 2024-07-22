import logging
import rich

from bingqilin.management import get_app_settings

logger = logging.getLogger("default-init-script")

settings = get_app_settings()

rich.print("[blue]Bingqilin app settings loaded![/blue]")
