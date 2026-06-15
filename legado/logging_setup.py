import logging
import os
import sys
from typing import Final

_log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hmpcf_painel.log")

_handlers: list[logging.Handler] = [
    logging.FileHandler(_log_file, encoding="utf-8"),
]
if sys.stdout:
    _handlers.append(logging.StreamHandler(sys.stdout))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=_handlers,
)

logger: Final = logging.getLogger("hmpcf")
