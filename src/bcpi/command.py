import argparse

from pathlib import Path

from .core import core_system

def cmdline() -> None:

    parser = argparse.ArgumentParser(
        description = 'bcpi - Brain Computer Interface on the Raspberry Pi'
    )

    parser.add_argument( 
        '--data-dir',
        type = lambda x: Path( x ),
        help = "Directory to store samples and models",
        default = Path.home() / 'bcpi-data'
    )

    parser.add_argument(
        '--port',
        type = int,
        help = 'Port to run Panel dashboard server on (default: pick a random open port)',
        default = 0
    )

    class Args:
        data_dir: Path
        port: int

    args = parser.parse_args(namespace=Args)

    core_system(data_dir = args.data_dir, port = args.port)