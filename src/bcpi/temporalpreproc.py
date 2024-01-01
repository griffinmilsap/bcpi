from dataclasses import field

import ezmsg.core as ez
from ezmsg.util.messages.axisarray import AxisArray

from ezmsg.sigproc.butterworthfilter import ButterworthFilter, ButterworthFilterSettings
from ezmsg.sigproc.decimate import Decimate, DownsampleSettings
from ezmsg.sigproc.ewmfilter import EWMFilter, EWMFilterSettings

class TemporalPreprocSettings( ez.Settings ):
    # 1. Bandpass Filter
    filt_settings: ButterworthFilterSettings = field( 
        default_factory = ButterworthFilterSettings
    )

    # X. TODO: Common Average Reference/Spatial Filtering?

    # 2. Downsample
    decimate_settings: DownsampleSettings = field(
        default_factory = DownsampleSettings
    )

    # 3. Exponentially Weighted Standardization
    ewm_history_dur: float = 2.0 # sec


class TemporalPreproc( ez.Collection ):

    SETTINGS: TemporalPreprocSettings

    INPUT_SIGNAL = ez.InputStream( AxisArray )
    OUTPUT_SIGNAL = ez.OutputStream( AxisArray )

    # Subunits
    BPFILT = ButterworthFilter()
    DECIMATE = Decimate()
    EWM = EWMFilter()

    def configure( self ) -> None:
        self.BPFILT.apply_settings(self.SETTINGS.filt_settings)
        self.DECIMATE.apply_settings(self.SETTINGS.decimate_settings)
        self.EWM.apply_settings(
            EWMFilterSettings(
                axis = 'time',
                history_dur = self.SETTINGS.ewm_history_dur,
            )
        )

    def network( self ) -> ez.NetworkDefinition:
        return (
            ( self.INPUT_SIGNAL, self.DECIMATE.INPUT_SIGNAL),
            ( self.DECIMATE.OUTPUT_SIGNAL, self.BPFILT.INPUT_SIGNAL ),
            ( self.BPFILT.OUTPUT_SIGNAL, self.EWM.INPUT_SIGNAL ),
            ( self.EWM.OUTPUT_SIGNAL, self.OUTPUT_SIGNAL )
        )