import tempfile

from pathlib import Path

import pytest

from ezmsg.gadget.install import (
    install, 
    uninstall,
    _MODULES_DIR,
    _SERVICE_DIR,
    _CONFIG_DIR
)

def test_install():

    with tempfile.TemporaryDirectory() as fp:
        root = Path(fp)

        # Set up the relevant parts of this test filesystem
        _MODULES_DIR(root).mkdir(parents = True, exist_ok = False)
        _SERVICE_DIR(root).mkdir(parents = True, exist_ok = False)

        install(root, endpoint_service = True, yes = True, test = True)

        # TODO: Actually check the temp file system

        uninstall(root, yes = True, test = True)

        # TODO: Actually check the temp file system is EMPTY

if __name__ == '__main__':
    test_install()