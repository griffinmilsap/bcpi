import os
import sys
import typing
import asyncio

from pathlib import Path

import ezmsg.core as ez
import panel as pn

from param.parameterized import Event

from ezmsg.panel.tabbedapp import Tab, TabbedApp

class StrategyManagerSettings(ez.Settings):
    data_dir: Path

class StrategyManagerState(ez.State):
    shell: pn.widgets.Terminal

    main_tab: pn.viewable.Viewable
    main_file: pn.widgets.StaticText
    main_term: pn.widgets.Terminal
    start_main: pn.widgets.Button
    stop_main: pn.widgets.Button
    main_running: pn.indicators.LoadingSpinner

    sidebar: pn.viewable.Viewable
    content: pn.viewable.Viewable

    task: typing.Optional[asyncio.Task] = None

class StrategyManager(ez.Unit, Tab):
    SETTINGS: StrategyManagerSettings
    STATE: StrategyManagerState

    @property
    def tab_name(self) -> str:
        return 'Strategy Manager'

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
            width = 40,
            height = 40,
        )

        self.STATE.start_main = pn.widgets.Button(
            name = 'Start Main Strategy',
            button_type = 'success',
        )

        def on_start(_: Event) -> None:
            if entrypoint.exists():
                self.STATE.main_term.clear() # type: ignore
                self.STATE.main_term.subprocess.run(sys.executable, str(entrypoint))
            else:
                # Raise modal
                ...

        self.STATE.start_main.on_click(on_start)

        self.STATE.stop_main = pn.widgets.Button(
            name = 'Kill Main Strategy',
            button_type = 'danger',
        )

        def on_stop(_: Event) -> None:
            self.STATE.main_term.subprocess.kill() # type: ignore

        self.STATE.stop_main.on_click(on_stop)

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

        if entrypoint.exists():
            on_start(None)
        else:
            self.STATE.main_term.subprocess.run('ls', '-lah', str(entrypoint.parent))

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

        self.STATE.content = pn.Tabs(
            self.STATE.shell,
            self.STATE.main_tab,
            sizing_mode = 'stretch_both',
        )

        self.STATE.sidebar = pn.Card(
            title = 'File Upload',
            sizing_mode = 'stretch_width',
        )

    def sidebar(self) -> pn.viewable.Viewable:
        return self.STATE.sidebar
    
    def content(self) -> pn.viewable.Viewable:
        return self.STATE.content


class StrategyManagerApp(ez.Collection, TabbedApp):
    SETTINGS: StrategyManagerSettings

    STRATEGY = StrategyManager()

    def configure(self) -> None:
        self.STRATEGY.apply_settings(self.SETTINGS)

    @property
    def title(self) -> str:
        return 'Strategy Manager'
    
    @property
    def tabs(self) -> typing.List[Tab]:
        return [
            self.STRATEGY,
        ]


if __name__ == '__main__':

    from ezmsg.panel.application import Application, ApplicationSettings
    from ezmsg.util.debuglog import DebugLog

    strat_app = StrategyManagerApp(
        StrategyManagerSettings(
            data_dir = Path('~/bcpi-data').expanduser()
        )
    )

    app = Application(
        ApplicationSettings(
            port = 0
        )
    )

    log = DebugLog()

    app.panels = {
        'strategy': strat_app.app
    }

    ez.run(
        APP = app,
        STRATEGY = strat_app,
        LOG = log,
    )

    