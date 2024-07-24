import logging

from dataclasses import dataclass, field
from typing import Optional, Dict

from bingqilin.conf.models import ConfigModelType


@dataclass
class ManagementCommandConfig:
    require_app_config: bool


@dataclass
class ManagementContextObj:
    settings_manager_env_name: str
    config: Optional[ConfigModelType] = None  # type: ignore
    loglevel: int = logging.INFO
    command_config: Dict[str, ManagementCommandConfig] = field(default_factory=dict)
