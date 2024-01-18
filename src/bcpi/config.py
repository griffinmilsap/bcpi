import os
import typing

from configparser import ConfigParser
from pathlib import Path
from importlib.resources import files

from ezmsg.unicorn.device import UnicornSettings

CONFIG_ENV = 'BCPI_CONFIG'
CONFIG_PATH = Path.home() / '.config' / 'bcpi'
CONFIG_FILE = 'bcpi.conf'

def _get_config_path(config_path: typing.Optional[Path] = None) -> Path:
    if config_path is None:
        config_path = Path(os.environ.get(CONFIG_ENV, CONFIG_PATH))
    return config_path.expanduser()

class BCPIConfig:

    parser: ConfigParser

    def __init__(self, config_path: typing.Optional[Path] = None):
        config_path = _get_config_path(config_path)

        config_files = []
        if config_path.exists():
            if config_path.is_file():
                config_files.append(config_path)
            elif config_path.is_dir():
                for fname in config_path.glob('*'):
                    config_files.append(fname)
                    
        config_dir = config_path.with_suffix('.d')
        if config_dir.exists() and config_dir.is_dir():
            for fname in config_dir.glob('*'):
                config_files.append(fname)

        self.parser = ConfigParser()
        self.parser.read(config_files)

    @property
    def unicorn_settings(self) -> UnicornSettings:
        address = self.parser.get('unicorn', 'address', fallback = 'simulator')
        n_samp = int(self.parser.get('unicorn', 'n_samp', fallback = '50'))
        return UnicornSettings(
            address = address,
            n_samp = n_samp
        )
    
    @property
    def graph_address(self) -> typing.Optional[typing.Tuple[str, int]]:
        graphserver = self.parser.get('ezmsg', 'graphserver', fallback = 'localhost:25978')
        if graphserver == 'any':
            graphserver = None
        else:
            host, port = graphserver.split(':')
            graphserver = (host, int(port))
        return graphserver
    
    @property
    def data_dir(self) -> Path:
        data_dir = self.parser.get('bcpi', 'data_dir', fallback = '~/bcpi-data')
        return Path(data_dir).expanduser()
    
    @property
    def port(self) -> int:
        return int(self.parser.get('bcpi', 'port', fallback = '8888'))
    

def create_config(config_path: typing.Optional[Path] = None) -> None:
    config_path = _get_config_path(config_path)

    data_files = files('bcpi')
    config_fname = config_path / CONFIG_FILE
    config_fname.parent.mkdir(parents = True, exist_ok = True)

    with open(config_fname, 'w') as config_f:
        config_f.write(data_files.joinpath(CONFIG_FILE).read_text())
    