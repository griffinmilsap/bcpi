import argparse
import typing

from pathlib import Path

import ezmsg.core as ez

from ezmsg.gadget.config import GadgetConfig
from ezmsg.gadget.hiddevice import hid_devices

from .config import CONFIG_PATH, CONFIG_ENV, create_config
from .install import install, uninstall


class BCPIArgs:
    config: typing.Optional[Path]
    only_core: bool
    single_process: bool
    create_config: bool
    install: bool
    uninstall: bool


def cmdline() -> None:

    parser = argparse.ArgumentParser(
        description = 'bcpi - Brain Computer Interface on the Raspberry Pi'
    )

    parser.add_argument( 
        '--config',
        type = lambda x: Path(x),
        help = f'config path for bcpi (default = {CONFIG_PATH}, or set {CONFIG_ENV})',
        default = None
    )

    parser.add_argument(
        '--only-core',
        action = 'store_true',
        help = 'launch the minimal (core) subset of functionality for realtime inferencing'
    )

    parser.add_argument(
        '--single-process',
        action = 'store_true',
        help = 'ensure all units run in single process (lower memory footprint)'
    )

    parser.add_argument(
        '--create-config',
        action = 'store_true',
        help = 'create a config file at --config and exit'
    )

    parser.add_argument(
        '--install',
        action = 'store_true',
        help = 'install systemd services to start an ezmsg graphserver and bcpi at system boot'
    )

    parser.add_argument(
        '--uninstall',
        action = 'store_true',
        help = 'uninstall bcpi-related systemd services'
    )

    args = parser.parse_args(namespace=BCPIArgs)

    if args.create_config:
        create_config(config_path = args.config)
    elif args.install:
        ...
    elif args.uninstall:
        ...
    else:
        launch(config_path = args.config, only_core = args.only_core, single_process = args.single_process)


def launch(config_path: typing.Optional[Path] = None, only_core: bool = False, single_process: bool = False) -> None:
    
    from .config import BCPIConfig
    from .core import BCPICore, BCPICoreSettings
    from .app import BCPI, BCPISettings

    config = BCPIConfig(config_path = config_path)

    if only_core:
        system = BCPICore(
            BCPICoreSettings(
                config_path = config_path,
            )
        )
    else:
        system = BCPI(
            BCPISettings(
                config_path = config_path
            )
        )

    gadget_config = GadgetConfig()
    hid_units = hid_devices(gadget_config)

    ez.logger.info(f'Accessable HID Devices: {hid_units}')

    components: typing.Dict[str, ez.Component] = dict(
        SYSTEM = system,
        **hid_units
    )

    if isinstance(system, BCPI):
        from ezmsg.panel.application import Application, ApplicationSettings

        app = Application(
            ApplicationSettings(
                port = config.port
            )
        )

        app.panels = {
            'bcpi': system.app,
        }

        components['APP'] = app

    ez.run(
        components = components,
        force_single_process = single_process,
        graph_address = config.graph_address,
    )

if __name__ == '__main__':
    cmdline()