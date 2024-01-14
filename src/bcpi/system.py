import os
import sys
import typing
import asyncio
import logging

from pathlib import Path

import ezmsg.core as ez
import panel as pn

pn.extension('terminal')

from param.parameterized import Event

from ezmsg.panel.tabbedapp import Tab, TabbedApp

class SystemTabSettings(ez.Settings):
    data_dir: Path

class SystemTabState(ez.State):
    shell: pn.widgets.Terminal

    main_tab: pn.viewable.Viewable
    main_file: pn.widgets.StaticText
    main_term: pn.widgets.Terminal
    start_main: pn.widgets.Button
    stop_main: pn.widgets.Button
    main_running: pn.indicators.LoadingSpinner

    log_term: pn.widgets.Terminal

    shutdown_button: pn.widgets.Button
    reboot_button: pn.widgets.Button

    sidebar: pn.viewable.Viewable
    content: pn.viewable.Viewable

    task: typing.Optional[asyncio.Task] = None

class SystemTab(ez.Unit, Tab):
    SETTINGS: SystemTabSettings
    STATE: SystemTabState

    @property
    def tab_name(self) -> str:
        return 'System'

    async def initialize(self) -> None:

        self.STATE.shell = pn.widgets.Terminal(
            options = {"cursorBlink": True},
            sizing_mode = 'stretch_both',
            name = 'Shell'
        )

        shell = os.environ['SHELL']
        self.STATE.shell.subprocess.run(shell)

        def on_shell_exit(event: Event) -> None:
            if event.new == False:
                self.STATE.shell.clear() # type: ignore
                self.STATE.shell.subprocess.run(shell)

        self.STATE.shell.subprocess.param.watch(on_shell_exit, 'running', onlychanged = True)

        entrypoint = self.SETTINGS.data_dir / 'strategy' / 'main.py'
        if not entrypoint.parent.exists():
            entrypoint.parent.mkdir(parents = True, exist_ok = True)

        self.STATE.main_term = pn.widgets.Terminal(
            sizing_mode = 'stretch_both',
        )

        self.STATE.main_running = pn.indicators.LoadingSpinner(
            value = False,
            color = 'primary',
            width = 35,
            height = 35,
        )

        self.STATE.start_main = pn.widgets.Button(
            name = 'Start Main Strategy',
            button_type = 'success',
        )

        def start_main(_: typing.Optional[Event] = None) -> None:
            if entrypoint.exists():
                self.STATE.main_term.clear() # type: ignore
                self.STATE.main_term.subprocess.run(sys.executable, str(entrypoint))
            else:
                errmsg = f'ERROR: Entrypoint does not exist: {str(entrypoint)}'
                self.STATE.main_term.subprocess.run('echo', errmsg)

        self.STATE.start_main.on_click(start_main)

        self.STATE.stop_main = pn.widgets.Button(
            name = 'Kill Main Strategy',
            button_type = 'danger',
        )

        def stop_main(_: typing.Optional[Event] = None) -> None:
            self.STATE.main_term.subprocess.kill() # type: ignore

        self.STATE.stop_main.on_click(stop_main)

        self.STATE.main_file = pn.widgets.StaticText(
            name = 'Main Entrypoint',
            value = str(entrypoint)
        )

        def main_running(event: Event) -> None:
            if event.new == True: # Just started running
                self.STATE.start_main.disabled = True
                self.STATE.stop_main.disabled = False
                self.STATE.main_running.value = True
            elif event.new == False: # Just stopped running
                self.STATE.start_main.disabled = False
                self.STATE.stop_main.disabled = True
                self.STATE.main_running.value = False

        self.STATE.main_term.subprocess.param.watch(main_running, 'running', onlychanged = True)

        start_main()

        self.STATE.main_tab = pn.Column(
            self.STATE.main_file,
            pn.Row(
                self.STATE.start_main,
                self.STATE.stop_main,
                self.STATE.main_running,
            ),
            self.STATE.main_term,
            name = 'Main Strategy'
        )

        self.STATE.log_term = pn.widgets.Terminal(
            sizing_mode = 'stretch_both',
            name = 'Log'
        )

        stream_handler = logging.StreamHandler(self.STATE.log_term)
        stream_handler.terminator = "  \n"
        formatter = logging.Formatter(
            "%(asctime)s.%(msecs)03d - pid: %(process)d - %(threadName)s "
            + "- %(levelname)s - %(funcName)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        stream_handler.setFormatter(formatter)
        ez.logger.addHandler(stream_handler)

        self.STATE.content = pn.Tabs(
            # self.STATE.log_term,
            # self.STATE.main_tab,
            # self.STATE.shell,
            min_height = 600,
            sizing_mode = 'stretch_both',
        )

        self.STATE.shutdown_button = pn.widgets.Button(
            name = 'Shutdown',
            button_type = 'danger',
            sizing_mode = 'stretch_width'
        )

        def shutdown_system(_: Event) -> None:
            ez.logger.warning('Shutting down system...')
            stop_main()
            self.STATE.main_term.subprocess.run('sudo', 'systemctl', 'poweroff')

        self.STATE.shutdown_button.on_click(shutdown_system)

        self.STATE.reboot_button = pn.widgets.Button(
            name = 'Reboot',
            button_type = 'warning',
            sizing_mode = 'stretch_width'
        )

        def reboot_system(_: Event) -> None:
            ez.logger.warning('Rebooting system...')
            stop_main()
            self.STATE.main_term.subprocess.run('sudo', 'systemctl', 'reboot')

        self.STATE.reboot_button.on_click(reboot_system)

        self.STATE.sidebar = pn.Card(
            self.STATE.reboot_button,
            self.STATE.shutdown_button,
            title = 'Power Controls',
            sizing_mode = 'stretch_width',
        )

    def sidebar(self) -> pn.viewable.Viewable:
        return self.STATE.sidebar
    
    def content(self) -> pn.viewable.Viewable:
        return self.STATE.content


class SystemApp(ez.Collection, TabbedApp):
    SETTINGS: SystemTabSettings

    SYSTEM = SystemTab()

    def configure(self) -> None:
        self.SYSTEM.apply_settings(self.SETTINGS)

    @property
    def title(self) -> str:
        return 'System Manager'
    
    @property
    def tabs(self) -> typing.List[Tab]:
        return [
            self.SYSTEM,
        ]


if __name__ == '__main__':

    from ezmsg.panel.application import Application, ApplicationSettings
    from ezmsg.util.debuglog import DebugLog

    sys_app = SystemApp(
        SystemTabSettings(
            data_dir = Path('~/bcpi-data').expanduser()
        )
    )

    app = Application(
        ApplicationSettings(
            port = 8888
        )
    )

    log = DebugLog()

    app.panels = {
        'system': sys_app.app
    }

    ez.run(
        APP = app,
        SYSTEM = sys_app,
        LOG = log,
    )

    