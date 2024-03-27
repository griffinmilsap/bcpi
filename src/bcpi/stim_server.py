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


class StimServerSettings(ez.Settings):
    service_name = "Stim Service"
    service_uuid: str = "A07498CA-AD5B-474E-940D-16F1FBE7E8CD"
    stim_char_uuid: str = "51FF12BB-3ED8-46E5-B4F9-D64E2FEC021B"
    trig_char_uuid: str = "51FF12BB-3ED8-46E5-B4F9-D64E2FEC021C"

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
            name = self.SETTINGS.service_name,
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
            value = None, 
            permissions = (
                GATTAttributePermissions.readable 
                | GATTAttributePermissions.writeable
            )
        )

        ez.logger.info(self.STATE.server.get_characteristic(self.SETTINGS.stim_char_uuid))
        await self.STATE.server.start()
        ez.logger.info("Advertising")

        # await asyncio.sleep(2)
        # ez.logger.info("Updating")
        # server.get_characteristic(my_char_uuid)
        # server.update_value(my_service_uuid, my_char_uuid)
        # await asyncio.sleep(5)
        # await server.stop()

    def read_request(self, characteristic: BlessGATTCharacteristic, **kwargs) -> bytearray:
        ez.logger.info(f"Reading {characteristic.value}")
        return characteristic.value

    def write_request(self, characteristic: BlessGATTCharacteristic, value: typing.Any, **kwargs):
        characteristic.value = value
        ez.logger.info(f"Char value set to {characteristic.value}")
        if characteristic.value == b"\x0f":
            ez.logger.info("NICE")

    async def shutdown(self) -> None:
        await self.STATE.server.stop()

    @ez.subscriber(INPUT_STIM)
    async def on_stim(self, msg: StimMessage) -> None:
        ez.logger.info(f'{msg.serialize()=}')
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