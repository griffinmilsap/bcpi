import asyncio
import typing

from bless import ( 
    BlessServer, # type: ignore
    BlessGATTCharacteristic,# type: ignore
    GATTCharacteristicProperties, # type: ignore
    GATTAttributePermissions # type: ignore
)

import ezmsg.core as ez

from ezmsg.sigproc.sampler import SampleTriggerMessage

from .messages import StimMessage

STIM_SERVICE_NAME = 'BCPIStim'
DEFAULT_SERVICE_UUID = "A07498CA-AD5B-474E-940D-16F1FBE7E8CD"
DEFAULT_STIM_CHAR_UUID = "51FF12BB-3ED8-46E5-B4F9-D64E2FEC021B"
DEFAULT_TRIG_CHAR_UUID = "51FF12BB-3ED8-46E5-B4F9-D64E2FEC021C"


class StimServerSettings(ez.Settings):
    service_uuid: str = DEFAULT_SERVICE_UUID
    stim_char_uuid: str = DEFAULT_STIM_CHAR_UUID
    trig_char_uuid: str = DEFAULT_TRIG_CHAR_UUID

class StimServerState(ez.State):
    server: BlessServer

class StimServer(ez.Unit):
    SETTINGS: StimServerSettings
    STATE: StimServerState

    INPUT_STIM = ez.InputStream(StimMessage)
    OUTPUT_TRIGGER = ez.OutputStream(SampleTriggerMessage)

    async def initialize(self) -> None:

        # Instantiate the server
        self.STATE.server = BlessServer(
            name = STIM_SERVICE_NAME,
            loop = asyncio.get_running_loop()
        )

        self.STATE.server.read_request_func = self.read_request
        self.STATE.server.write_request_func = self.write_request

        # Add Service
        await self.STATE.server.add_new_service(self.SETTINGS.service_uuid)

        # Add the stim characteristic to the service
        await self.STATE.server.add_new_characteristic(
            service_uuid = self.SETTINGS.service_uuid, 
            char_uuid = self.SETTINGS.stim_char_uuid, 
            properties = (
                GATTCharacteristicProperties.read
                | GATTCharacteristicProperties.write
                | GATTCharacteristicProperties.indicate
            ), 
            value = bytearray(int.to_bytes(0xface, 2, 'big')), 
            permissions = (
                GATTAttributePermissions.readable 
                | GATTAttributePermissions.writeable
            )
        )

        await self.STATE.server.start()
        ez.logger.info("Advertising")

    def read_request(self, characteristic: BlessGATTCharacteristic, **kwargs) -> bytearray:
        ez.logger.info(f"Reading {characteristic.value}")
        return characteristic.value

    def write_request(self, characteristic: BlessGATTCharacteristic, value: typing.Any, **kwargs):
        characteristic.value = value
        ez.logger.info(f"Char value set to {characteristic.value}")

    async def shutdown(self) -> None:
        await self.STATE.server.stop()

    @ez.subscriber(INPUT_STIM)
    async def on_stim(self, msg: StimMessage) -> None:
        self.STATE.server.get_characteristic(self.SETTINGS.stim_char_uuid)
        self.STATE.server.update_value(self.SETTINGS.service_uuid, self.SETTINGS.stim_char_uuid)


if __name__ == '__main__':

    ## Test/devel apparatus
    
    from ezmsg.util.debuglog import DebugLog
    from ezmsg.panel.application import Application, ApplicationSettings

    import panel as pn
    from ezmsg.panel.tabbedapp import Tab

    class StimControlsSettings(ez.Settings):
        ...

    class StimControlsState(ez.State):
        output_queue: asyncio.Queue[StimMessage]
        send_button: pn.widgets.Button

    class StimControls(ez.Unit, Tab):
        SETTINGS: StimControlsSettings
        STATE: StimControlsState

        OUTPUT_STIM = ez.OutputStream(StimMessage)

        async def initialize(self) -> None:
            self.STATE.output_queue = asyncio.Queue()
            self.STATE.send_button = pn.widgets.Button(name = 'Send', button_type = 'primary', sizing_mode = 'stretch_width')

            self.STATE.send_button.on_click(lambda _:
                self.STATE.output_queue.put_nowait(
                    StimMessage()
                )
            )

        @property
        def title(self) -> str:
            return 'Stim Controls'
        
        def sidebar(self) -> pn.viewable.Viewable:
            return pn.Card(
                pn.Column(
                    self.STATE.send_button,
                ),
                title = f'{self.title} Sidebar',
            )
        
        def content(self) -> pn.viewable.Viewable:
            return pn.Card(
                title = f'{self.title} Content',
                sizing_mode = 'stretch_both'
            )

        @ez.publisher(OUTPUT_STIM)
        async def output(self) -> typing.AsyncGenerator:
            while True:
                msg = await self.STATE.output_queue.get()
                yield self.OUTPUT_STIM, msg

    log = DebugLog()

    stim_gatt = StimServer(
        StimServerSettings(
        )
    )

    controls = StimControls(
        StimControlsSettings(
        )
    )

    app = Application(
        ApplicationSettings(
            port = 8888,
        )
    )

    app.panels = {
        'controls': controls.app
    }

    ez.run(
        STIM_GATT = stim_gatt,
        LOG = log,
        CONTROLS = controls,
        APP = app,

        connections = (
            (controls.OUTPUT_STIM, stim_gatt.INPUT_STIM),
        )
    )