import typing
from pathlib import Path

import ezmsg.core as ez

from ezmsg.unicorn.dashboard import UnicornDashboard, UnicornDashboardSettings

from ezmsg.sigproc.butterworthfilter import ButterworthFilterSettings
from ezmsg.sigproc.decimate import DownsampleSettings
from ezmsg.sigproc.signalinjector import SignalInjector, SignalInjectorSettings
from ezmsg.tasks.frequencymapper import FrequencyMapper, FrequencyMapperSettings

from ezmsg.fbcsp.inference import Inference, InferenceSettings

from .temporalpreproc import TemporalPreproc, TemporalPreprocSettings
from .config import BCPIConfig
from .system import SystemTab, SystemTabSettings
from .topics import BCPITopics

class BCPICoreSettings(ez.Settings):
    config_path: typing.Optional[Path] = None

class BCPICore(ez.Collection):
    SETTINGS: BCPICoreSettings

    INPUT_INFERENCE_SETTINGS = ez.InputStream(InferenceSettings)

    SYSTEM_TAB = SystemTab()
    UNICORN = UnicornDashboard()
    MAPPER = FrequencyMapper()
    INJECTOR = SignalInjector()
    PREPROC = TemporalPreproc()

    INFERENCE = Inference()

    def configure(self) -> None:
        config = BCPIConfig(self.SETTINGS.config_path)

        self.SYSTEM_TAB.apply_settings(
            SystemTabSettings(
                data_dir = config.data_dir,
            )
        )

        self.UNICORN.apply_settings(
            UnicornDashboardSettings(
                device_settings = config.unicorn_settings
            )
        )

        self.INJECTOR.apply_settings(
            SignalInjectorSettings(
                time_dim = 'time',
                mixing_seed = 0xDEADBEEF
            )
        )

        self.MAPPER.apply_settings(
            FrequencyMapperSettings(
                mapping = {
                    'INJECT_12': 12.0, # Hz
                    'INJECT_15': 15.0, # Hz
                    'INJECT_17': 17.0, # Hz
                    'INJECT_20': 20.0, # Hz
                }
            )
        )

        self.PREPROC.apply_settings(
            TemporalPreprocSettings(
                filt_settings = ButterworthFilterSettings(
                    axis = 'time',
                    order = 3, # Butterworth filter order
                    cuton = 5, # Cuton (Hz)
                    cutoff = 50, # Cutoff (Hz)
                ),
                decimate_settings = DownsampleSettings(
                    axis = 'time',
                    factor = 2
                ),
                ewm_history_dur = 2.0
            )
        )

        self.INFERENCE.apply_settings(
            InferenceSettings(
                model_path = config.data_dir / 'models' / 'boot.model'
            )
        )

    def network(self) -> ez.NetworkDefinition:
        return (
            (self.UNICORN.OUTPUT_ACCELEROMETER, BCPITopics.ACCELEROMETER),
            (self.UNICORN.OUTPUT_GYROSCOPE, BCPITopics.GYROSCOPE),
            (self.UNICORN.OUTPUT_SIGNAL, self.INJECTOR.INPUT_SIGNAL),
            (self.INJECTOR.OUTPUT_SIGNAL, BCPITopics.EPHYS),
            (self.INJECTOR.OUTPUT_SIGNAL, self.PREPROC.INPUT_SIGNAL),
            (self.PREPROC.OUTPUT_SIGNAL, BCPITopics.EPHYS_PREPROC),

            (BCPITopics.TARGET, self.MAPPER.INPUT_CLASS),
            (self.MAPPER.OUTPUT_FREQUENCY, self.INJECTOR.INPUT_FREQUENCY),
            (self.PREPROC.OUTPUT_SIGNAL, self.INFERENCE.INPUT_SIGNAL),
            
            (self.INPUT_INFERENCE_SETTINGS, self.INFERENCE.INPUT_SETTINGS),
            (self.INFERENCE.OUTPUT_DECODE, BCPITopics.DECODE),
            (self.INFERENCE.OUTPUT_CLASS, BCPITopics.CLASS),
        )
