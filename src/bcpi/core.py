import typing
from pathlib import Path

import ezmsg.core as ez

from ezmsg.unicorn.device import UnicornDevice, UnicornDeviceSettings
from ezmsg.gadget.hiddevice import hid_devices
from ezmsg.gadget.config import GadgetConfig

from ezmsg.sigproc.butterworthfilter import ButterworthFilterSettings
from ezmsg.sigproc.decimate import DownsampleSettings
from ezmsg.sigproc.signalinjector import SignalInjector, SignalInjectorSettings
from ezmsg.tasks.frequencymapper import FrequencyMapper, FrequencyMapperSettings

from ezmsg.fbcsp.inference import Inference, InferenceSettings

from .temporalpreproc import TemporalPreproc, TemporalPreprocSettings
from .config import BCPIConfig
from .system import SystemTab, SystemTabSettings


EPHYS_TOPIC = 'EPHYS' # AxisArray -- Electrophysiology
EPHYS_PREPROC_TOPIC = 'EPHYS_PREPROC' # AxisArray -- Preprocessed Electrophysiology
ACCELEROMETER_TOPIC = 'ACCEL' # AxisArray -- Accelerometer timeseries from device
GYROSCOPE_TOPIC = 'GYRO' # AxisArray -- Gyroscope timeseries from device
DECODE_TOPIC = 'DECODE' # ClassDecodeMessage -- Posterior Decoder Probabilities
CLASS_TOPIC = 'CLASS' # typing.Optional[str] -- Decoded class
TARGET_TOPIC = 'TARGET' # typing.Optional[str] -- Target class (from Task)
TRIAL_TOPIC = 'TRIAL' # SampleMessage -- Clipped trial data (Preprocessed)


class BCPICoreSettings(ez.Settings):
    config_path: typing.Optional[Path] = None

class BCPICore(ez.Collection):
    SETTINGS: BCPICoreSettings

    SYSTEM_TAB = SystemTab()
    UNICORN = UnicornDevice()
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
                config.unicorn_settings
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
            (self.UNICORN.OUTPUT_ACCELEROMETER, ACCELEROMETER_TOPIC),
            (self.UNICORN.OUTPUT_GYROSCOPE, GYROSCOPE_TOPIC),
            (self.UNICORN.OUTPUT_SIGNAL, self.INJECTOR.INPUT_SIGNAL),
            (self.INJECTOR.OUTPUT_SIGNAL, EPHYS_TOPIC),
            (EPHYS_TOPIC, self.PREPROC.INPUT_SIGNAL),
            (self.PREPROC.OUTPUT_SIGNAL, EPHYS_PREPROC_TOPIC),

            (TARGET_TOPIC, self.MAPPER.INPUT_CLASS),
            (self.MAPPER.OUTPUT_FREQUENCY, self.INJECTOR.INPUT_FREQUENCY),
            (EPHYS_PREPROC_TOPIC, self.INFERENCE.INPUT_SIGNAL),

            (self.INFERENCE.OUTPUT_DECODE, DECODE_TOPIC),
            (self.INFERENCE.OUTPUT_CLASS, CLASS_TOPIC)
        )


def core_system(config_path: typing.Optional[Path] = None) -> None:

    config = BCPIConfig(config_path = config_path)

    system = BCPICore(
        BCPICoreSettings(
            config_path = config_path
        )
    )

    gadget_config = GadgetConfig()
    hid_units = hid_devices(gadget_config)

    ez.logger.info(f'Accessable HID Devices: {hid_units}')

    components = dict(
        SYSTEM = system,
        **hid_units
    )

    ez.run(
        components = components,
        # We're pretty memory constrained on some Pi platforms,
        # multiprocessing may really help us, but the memory hit is
        # substantial.  
        # `import torch` uses ~100MB of memory per-process
        # `import panel` uses ~61MB of memory per-process
        # The pizero2w only has 512 MB of system memory..
        force_single_process = True,
        graph_address = config.graph_address,
    )