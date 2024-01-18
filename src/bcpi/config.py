import os
import typing

from configparser import ConfigParser

from pathlib import Path

from ezmsg.unicorn.device import UnicornSettings

CONFIG_ENV = 'BCPI_CONFIG'
CONFIG_PATH = '/etc/bcpi.conf'

class BCPIConfig:

    parser: ConfigParser

    def __init__(self, config_path: typing.Optional[Path] = None):
        if config_path is None:
            config_path = Path(os.environ.get(CONFIG_ENV, CONFIG_PATH))
        
        config_path = config_path.expanduser()

        config_files = []
        if config_path.exists() and config_path.is_file():
            config_files.append(config_path)
        config_dir = config_path.with_suffix('.d')
        if config_dir.exists() and config_dir.is_dir():
            for fname in config_dir.glob('*'):
                config_files.append(fname)

        self.parser = ConfigParser()
        self.parser.read(config_files)

    @property
    def unicorn_settings(self) -> UnicornSettings:
        address = self.parser.get('unicorn', 'address', fallback = 'simulator')
        n_samp = int(self.parser.get('unicorn', 'n_samp', fallback = 50))
        return UnicornSettings(
            address = address,
            n_samp = n_samp
        )
    
    @property
    def graph_address(self) -> typing.Tuple[str, int]:
        remote_host = self.parser.get('ezmsg', 'graph_host', fallback = 'localhost')
        remote_port = int(self.parser.get('ezmsg', 'graph_port', fallback = '25978'))
        return remote_host, remote_port
    
    @property
    def data_dir(self) -> Path:
        data_dir = self.parser.get('bcpi', 'data_dir', fallback = '~/bcpi-data')
        return Path(data_dir).expanduser()
    
    @property
    def port(self) -> int:
        return int(self.parser.get('bcpi', 'port', fallback = '8888'))


    