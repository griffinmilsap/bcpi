import typing
from dataclasses import dataclass, field

import numpy as np
from numpy.linalg import svd

import ezmsg.core as ez
from ezmsg.util.generator import consumer
from ezmsg.util.messages.axisarray import AxisArray
from ezmsg.sigproc.sampler import SampleMessage


@dataclass
class FrequencyDecodeMessage(AxisArray):
    freqs: typing.List[float] = field(default_factory = list)


@consumer
def frequency_decode(
    time_axis: typing.Union[str, int] = 0,
    harmonics: int = 0,
    freqs: typing.List[float] = [],
    max_int_time: float = 0
) -> typing.Generator[typing.Optional[FrequencyDecodeMessage], typing.Union[SampleMessage, AxisArray], None]:
    """
    # `frequency_decode`
    Evaluates the presence of periodic content at various frequencies in the input signal using CCA  
    
    ## Further reading:  
    * [Nakanishi et. al. 2015](https://doi.org/10.1371%2Fjournal.pone.0140703)
    
    ## Parameters:
    * `time_axis (str|int)`: The time axis in the data array to look for periodic content within.
        Default: 0  - choose the first axis in the first input.

    * `harmonics (int)`: The number of additional harmonics beyond the fundamental to use for the 'design' matrix
        Many periodic signals are not pure sinusoids, and inclusion of higher harmonics can help evaluate the 
        presence of signals with higher frequency harmonic content
        Default: 0 - generate a design matrix using only the fundamental frequency.

    * `freqs (List[float])`: Frequencies (in hz) to evaluate the presence of within the input signal
        Default: [] an empty list; frequencies will be found within the input SampleMessages
        AxisArrays have no good place to put this metadata, so specify frequencies here if only AxisArrays
        will be passed as input to the generator.  If a SampleMessage is passed in, this generator looks
        at the `trigger` field of the SampleMessage (a SampleTriggerMessage) and looks for the `freqs` attribute
        within that trigger for a list of frequencies to evaluate.  This field is present in the 
        SSVEPSampleTriggerMessage defined in ezmsg.tasks.ssvep from the ezmsg-tasks package.

    * `max_int_t (float)`: Maximum integration time (in seconds) to use for calculation.  
        0 (default): Use all time provided for the calculation.
        Useful for artificially limiting the amount of data used for the CCA method to evaluate
        the necessary integration time for good decoding performance
 
    ## Sends:
    * `AxisArray` or `SampleMessage` containing buffers of data to evaluate
    Yields:
    * `FrequencyDecodeMessage | None`: "Posteriors" of frequency decoding
        This is calculated as the softmax of the highest canonical correlations between each design matrix and the data
    """
    
    harmonics = max(0, harmonics)
    max_int_time = max(0, max_int_time)
    output: typing.Optional[FrequencyDecodeMessage] = None

    while True:
        input = yield output 

        test_freqs = freqs
        if isinstance(input, SampleMessage):
            trigger = input.trigger
            input = input.sample
            if len(test_freqs) == 0:
                test_freqs = getattr(trigger, 'freqs', []) 

        t_ax = input.ax(time_axis)
        fs = 1.0 / t_ax.axis.gain
        t = t_ax.values - t_ax.axis.offset
        max_samp = int(max_int_time * fs) if max_int_time else len(t)
        t = t[:max_samp]

        if len(test_freqs) == 0:
            ez.logger.warning('no frequencies to test')
            output = None
            continue

        cv = []
        for test_freq in test_freqs:

            # Create the design matrix of base frequency and requested harmonics
            design = []
            for harm_idx in range(harmonics + 1):
                f = test_freq * (harm_idx + 1)
                w = 2.0 * np.pi * f * t
                design.append(np.sin(w))
                design.append(np.cos(w))
            design = np.array(design) # time is now dim 1

            # We only care about highest canonical correlation
            # which can be calculated using singular value decomposition
            # https://numerical.recipes/whp/notes/CanonCorrBySVD.pdf
            X = input.as2d(time_axis) # time-axis moved to dim 0, all other axes flattened to dim 1
            X = X - X.mean(0) # Method works best with zero-mean on time dimension.
            _, S, _ = svd(np.dot(design, input.as2d(time_axis)[:max_samp, ...]))

            # S is porportional to canonical correlations; SVD guarantees max corr is element 0
            cv.append(S[0]) 

        # Calculate softmax with shifting to avoid overflow
        # (https://doi.org/10.1093/imanum/draa038)
        cv = np.array(cv)
        cv = cv - cv.max()
        cv = np.exp(cv)
        softmax = cv / np.sum(cv)

        output = FrequencyDecodeMessage(
            softmax,
            dims = ['freq'],
            freqs = test_freqs
        )


class FrequencyDecodeSettings(ez.Settings):
    harmonics: int = 0
    time_axis: typing.Union[str, int] = 0
    freqs: typing.List[float] = field(default_factory = list)


class FrequencyDecodeState(ez.State):
    gen: typing.Generator[typing.Optional[FrequencyDecodeMessage], typing.Union[SampleMessage, AxisArray], None]


class FrequencyDecode(ez.Unit):
    SETTINGS: FrequencyDecodeSettings
    STATE: FrequencyDecodeState

    INPUT_SETTINGS = ez.InputStream(FrequencyDecodeSettings)
    INPUT_SIGNAL = ez.InputStream(typing.Union[AxisArray, SampleMessage])
    OUTPUT_FREQ = ez.OutputStream(typing.Optional[FrequencyDecodeMessage])

    async def create_generator(self, settings: FrequencyDecodeSettings) -> None:
        self.STATE.gen = frequency_decode(
            harmonics = settings.harmonics,
            time_axis = settings.time_axis,
            freqs = settings.freqs
        )

    async def initialize(self) -> None:
        await self.create_generator(self.SETTINGS)

    @ez.subscriber(INPUT_SETTINGS)
    async def on_settings(self, msg: FrequencyDecodeSettings) -> None:
        await self.create_generator(msg)

    @ez.subscriber(INPUT_SIGNAL)
    @ez.publisher(OUTPUT_FREQ)
    async def on_signal(self, msg: typing.Union[AxisArray, SampleMessage]) -> typing.AsyncGenerator:
        yield self.STATE.gen.send(msg)