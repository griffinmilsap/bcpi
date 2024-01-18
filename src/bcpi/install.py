
import typing

from subprocess import Popen, PIPE
from pathlib import Path
from importlib.resources import files

def _confirm_prompt(question: str, yes: bool = False) -> bool:
    reply = None if not yes else ""
    while reply not in ("", "y", "n"):
        reply = input(f"{question} (Y/n): ").lower()
    response = (reply in ("", "y"))
    if response:
        print(f'ACTION: {question}')
    return response

def _run_command(cmd: str, test_result: typing.Optional[bytes] = None) -> bytes:
    if test_result is None:
        process = Popen(cmd, stdout = PIPE, stderr = PIPE, shell = True)
        stdout, stderr = process.communicate()
        if stderr: print(stderr.strip())
        return stdout.strip()
    else:
        print(f'TEST -- NOT Running "{cmd}", assuming result: {test_result}')
        return test_result

_CONFIG_DIR = lambda root: root / 'etc'
_MODULES_DIR = lambda root: _CONFIG_DIR(root) / 'modules-load.d'
_SERVICE_DIR = lambda root: root / Path('lib/systemd/system')

CONFIG_FILE = 'ezmsg-gadget.conf'
BOOT_SERVICE_FILE = 'ezmsg-gadget.service'
ENDPOINT_SERVICE_FILE = 'ezmsg-gadget-endpoint.service'

def install(
        root: Path = Path('/'), 
        boot_service: bool = True, 
        endpoint_service: bool = False, 
        yes: bool = False,
        test: bool = False
    ) -> None:

    # CONFIGURE KERNEL MODULES
    modules_dir = _MODULES_DIR(root)

    if _confirm_prompt(f'Add dwc2 to {modules_dir}', yes):
        with open(modules_dir / 'dwc2.conf', 'w') as f:
            f.write('dwc2')

    if _confirm_prompt(f'Add libcomposite to {modules_dir}', yes):
        with open(modules_dir / 'libcomposite.conf', 'w') as f:
            f.write('libcomposite')

    data_files = files('ezmsg.gadget')

    # ADD CONFIG FILE
    config_dir = _CONFIG_DIR(root)
    config_file = 'ezmsg-gadget.conf'
    if _confirm_prompt(f'Add {config_file} to {config_dir}', yes):
        with open(config_dir / config_file, 'w') as config_f:
            config_f.write(data_files.joinpath(config_file).read_text())
    
    # ADD BOOT SERVICE
    service_dir = _SERVICE_DIR(root)
    boot_service_enabled = False

    if boot_service:
        print('Boot service: enumerate devices on boot')
        print('Why? Activating ezmsg-gadget requires root, so do it on boot automatically')
        if _confirm_prompt(f'Write {BOOT_SERVICE_FILE} to {service_dir}', yes):
            with open(service_dir / BOOT_SERVICE_FILE, 'w') as f:
                f.write(data_files.joinpath(BOOT_SERVICE_FILE).read_text())
            if _confirm_prompt('Issue "systemctl daemon-reload"', yes):
                _run_command('systemctl daemon-reload', test_result = b'' if test else None)

    # ENABLE BOOT SERVICE
    print('Checking if boot service is enabled...')
    boot_service_result = _run_command(
        f'systemctl is-enabled {BOOT_SERVICE_FILE}', 
        test_result = b'enabled' if test else None
    )
    print(f'Boot service status: {boot_service_result}')

    # CHECK IF BOOT SERVICE ENABLED
    if boot_service_result == b'enabled':
        print('Boot service enabled')
        boot_service_enabled = True
    elif boot_service_result == b'disabled':
        if boot_service and _confirm_prompt(f'Enable {BOOT_SERVICE_FILE}', yes):
            _run_command(
                f'systemctl enable {BOOT_SERVICE_FILE}', 
                test_result = b'' if test else None
            )

            boot_service_enabled = True
    else:
        print('Boot service not installed or enabled')

    # ADD ENDPOINT SERVICE
    if endpoint_service:
        print('Endpoint service: run an ezmsg endpoint to connect to remote graph server on boot')
        print('Why? This software is likely running on a headless single-board computer')
        if not boot_service_enabled:
            print('WARNING: This service requires the boot service to run.')
        if _confirm_prompt(f'Create user: ezmsg-gadget?', yes):
            _run_command(f'useradd ezmsg-gadget', test_result = b'' if test else None)
        else:
            print('WARNING: Endpoint service runs as user ezmsg-gadget...')
        if _confirm_prompt(f'Write {ENDPOINT_SERVICE_FILE} to {service_dir}', yes):
            with open(service_dir / ENDPOINT_SERVICE_FILE, 'w') as f:
                f.write(data_files.joinpath(ENDPOINT_SERVICE_FILE).read_text())
                if _confirm_prompt('Issue "systemctl daemon-reload"', yes):
                    _run_command('systemctl daemon-reload', test_result = b'' if test else None)

        # ENABLE ENDPOINT SERVICE
        print('Checking if endpoint service is enabled...')
        endpoint_service_result = _run_command(
            f'systemctl is-enabled {ENDPOINT_SERVICE_FILE}', 
            test_result = b'enabled' if test else None
        )
        print(f'Endpoint service status: {endpoint_service_result}')

        # CHECK IF ENDPOINT SERVICE ENABLED
        if endpoint_service_result == b'enabled':
            print('Endpoint service enabled')
        elif endpoint_service_result == b'disabled':
            if endpoint_service and _confirm_prompt(f'Enable {ENDPOINT_SERVICE_FILE}', yes):
                _run_command(
                    f'systemctl enable {ENDPOINT_SERVICE_FILE}', 
                    test_result = b'' if test else None
                )
        else:
            print('Endpoint service not installed or enabled')

    print("Install completed.  Reboot encouraged.")

def uninstall(root: Path = Path('/'), yes: bool = False, test: bool = False) -> None:

    # STOP/DISABLE SERVICES
    service_dir = _SERVICE_DIR(root)

    services: typing.List[Path] = [
        service_dir / BOOT_SERVICE_FILE,
        service_dir / ENDPOINT_SERVICE_FILE,
    ]

    daemon_reload = False
    for service in services:
        if service.exists():
            if _confirm_prompt(f'Stop {service.name}', yes):
                _run_command(
                    f'systemctl stop {service.name}', 
                    test_result = b'' if test else None
                )

            service_enabled_result = _run_command(
                f'systemctl is-enabled {service.name}', 
                test_result = b'enabled' if test else None
            )

            if service_enabled_result == b'enabled' and _confirm_prompt(f'Disable {service.name}', yes):
                _run_command(
                    f'systemctl disable {service.name}', 
                    test_result = b'' if test else None
                )

            if _confirm_prompt(f'Remove {service}', yes):
                service.unlink()
                daemon_reload = True

    if daemon_reload and _confirm_prompt('Issue "systemctl daemon-reload"', yes):
        _run_command('systemctl daemon-reload', test_result = b'' if test else None)

    if _confirm_prompt('Remove user: ezmsg-gadget', yes):
        _run_command('userdel ezmsg-gadget', test_result = b'' if test else None)

    modules_dir: Path = _MODULES_DIR(root)
    config_dir: Path = _CONFIG_DIR(root)

    # REMOVE ALL OTHER INSTALLED FILES
    files = services + [
        modules_dir / 'dwc2.conf',
        modules_dir / 'libcomposite.conf',
        config_dir / CONFIG_FILE
    ]

    for f in files:
        if f.exists() and _confirm_prompt(f'Remove {f}', yes):
            f.unlink()

    print("Uninstall completed.  Reboot encouraged.")