"""로깅 설정."""
import logging
import sys
from pathlib import Path

import yaml


def get_logger(name: str) -> logging.Logger:
    root = Path(__file__).parent.parent.parent
    with open(root / "config" / "settings.yaml") as f:
        settings = yaml.safe_load(f)

    log_cfg = settings.get("logging", {})
    level = getattr(logging, log_cfg.get("level", "INFO"))
    log_file = root / log_cfg.get("file", "data/trading.log")
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger
