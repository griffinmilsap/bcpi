import asyncio
import typing

from bleak import (
    BleakClient,
    BleakScanner,
)

import ezmsg.core as ez

from ezmsg.sigproc.sampler import SampleTriggerMessage

from .messages import StimMessage

class StimClientSettings(ez.Settings):
    ...

class StimClientState(ez.State):
    ...

class StimClient(ez.Unit):
    SETTINGS: StimClientSettings
    STATE: StimClientState

    OUTPUT_STIM = ez.OutputStream(StimMessage)
    INPUT_TRIGGER = ez.InputStream(SampleTriggerMessage)

    @ez.publisher(OUTPUT_STIM)
    async def pub_stims(self) -> typing.AsyncGenerator:
        ...

    @ez.subscriber(INPUT_TRIGGER)
    async def on_trig(self, msg: SampleTriggerMessage) -> None:
        ...

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