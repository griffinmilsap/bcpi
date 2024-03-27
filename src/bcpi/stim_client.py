import asyncio
import typing

from bleak import (
    BleakClient,
    BleakScanner,
)

import ezmsg.core as ez

from ezmsg.sigproc.sampler import SampleTriggerMessage

from .messages import StimMessage
from .stim_server import (
    DEFAULT_TRIG_CHAR_UUID, 
    DEFAULT_STIM_CHAR_UUID,
    STIM_SERVICE_NAME
)

class StimClientSettings(ez.Settings):
    name: str = STIM_SERVICE_NAME
    stim_char_uuid: str = DEFAULT_STIM_CHAR_UUID
    trig_char_uuid: str = DEFAULT_TRIG_CHAR_UUID

class StimClientState(ez.State):
    conn: BleakClient
    queue: asyncio.Queue

class StimClient(ez.Unit):
    SETTINGS: StimClientSettings
    STATE: StimClientState

    OUTPUT_STIM = ez.OutputStream(StimMessage)
    INPUT_TRIGGER = ez.InputStream(SampleTriggerMessage)

    async def initialize(self) -> None:
        device = await BleakScanner.find_device_by_name(self.SETTINGS.name, **{})
        if device is None:
            raise Exception("Device not found!")
        self.STATE.conn = BleakClient(device)
        await self.STATE.conn.connect()
        ez.logger.info("Connected to Stim Server")
        self.STATE.queue = asyncio.Queue()

        async def callback_handler(_, data):
            await self.STATE.queue.put(data)

        await self.STATE.conn.start_notify(self.SETTINGS.stim_char_uuid, callback_handler)

    async def shutdown(self) -> None:
        await self.STATE.conn.stop_notify(self.SETTINGS.stim_char_uuid)
        await self.STATE.conn.disconnect()


    @ez.publisher(OUTPUT_STIM)
    async def pub_stims(self) -> typing.AsyncGenerator:
        
        while True:
            # Await stim notification from stim characteristic
            data = await self.STATE.queue.get()

            msg = StimMessage(3)
            yield self.OUTPUT_STIM, msg


    @ez.subscriber(INPUT_TRIGGER)
    async def on_trig(self, msg: SampleTriggerMessage) -> None:
        # Send trigger to trigger characteristic
        ez.logger.info(f'{msg=}')

if __name__ == '__main__':

    class StimLoopback(ez.Unit):

        INPUT_STIM = ez.InputStream(StimMessage)
        OUTPUT_TRIGGER = ez.OutputStream(SampleTriggerMessage)

        @ez.subscriber(INPUT_STIM)
        @ez.publisher(OUTPUT_TRIGGER)
        async def on_stim(self, msg: StimMessage) -> typing.AsyncGenerator:
            await asyncio.sleep(msg.value)
            yield self.OUTPUT_TRIGGER, SampleTriggerMessage(period = (msg.value * -1.0, 0.0))

    stim_client = StimClient(
        StimClientSettings(
        )
    )

    loopback = StimLoopback()

    ez.run(
        CLIENT = stim_client,
        LOOPBACK = loopback,

        connections = (
            (stim_client.OUTPUT_STIM, loopback.INPUT_STIM),
            (loopback.OUTPUT_TRIGGER, stim_client.INPUT_TRIGGER)
        )
    )