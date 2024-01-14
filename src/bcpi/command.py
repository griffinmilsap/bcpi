import argparse
import typing

from pathlib import Path

from .app import core_system
from .config import CONFIG_PATH, CONFIG_ENV

def cmdline() -> None:

    parser = argparse.ArgumentParser(
        description = 'bcpi - Brain Computer Interface on the Raspberry Pi'
    )

    parser.add_argument( 
        '--config',
        type = lambda x: Path( x ),
        help = f'config path for bcpi (default = {CONFIG_PATH}, or set {CONFIG_ENV})',
        default = None
    )

    class Args:
        config: typing.Optional[Path]

    args = parser.parse_args(namespace=Args)

    core_system(args.config)