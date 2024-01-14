import typing
from pathlib import Path

import ezmsg.core as ez
from ezmsg.panel.application import Application, ApplicationSettings
from ezmsg.unicorn.dashboard import UnicornDashboardApp, UnicornDashboardSettings
from ezmsg.tasks.task import TaskSettings
from ezmsg.tasks.cuedactiontask import CuedActionTaskApp
from ezmsg.tasks.frequencymapper import FrequencyMapper, FrequencyMapperSettings
from ezmsg.gadget.hiddevice import hid_devices
from ezmsg.gadget.config import GadgetConfig

from ezmsg.sigproc.butterworthfilter import ButterworthFilterSettings
from ezmsg.sigproc.decimate import DownsampleSettings
from ezmsg.sigproc.signalinjector import SignalInjector, SignalInjectorSettings
from .temporalpreproc import TemporalPreproc, TemporalPreprocSettings
from .config import BCPIConfig
from .system import SystemApp, SystemTabSettings

EPHYS_TOPIC = 'EPHYS' # AxisArray -- Electrophysiology
EPHYS_PREPROC_TOPIC = 'EPHYS_PREPROC' # AxisArray -- Preprocessed Electrophysiology
ACCELEROMETER_TOPIC = 'ACCEL' # AxisArray -- Accelerometer timeseries from device
GYROSCOPE_TOPIC = 'GYRO' # AxisArray -- Gyroscope timeseries from device
DECODE_TOPIC = 'DECODE' # ClassDecodeMessage -- Posterior Decoder Probabilities
CLASS_TOPIC = 'CLASS' # typing.Optional[str] -- Decoded class
TARGET_TOPIC = 'TARGET' # typing.Optional[str] -- Target class (from Task)
TRIAL_TOPIC = 'TRIAL' # SampleMessage -- Clipped trial data (Preprocessed)

try:
    from ezmsg.fbcsp.dashboard.app import Dashboard, DashboardSettings
    FBCSP = True
except ImportError:
    FBCSP = False


def core_system(config_path: typing.Optional[Path] = None) -> None:

    config = BCPIConfig(config_path)

    system = SystemApp(
        SystemTabSettings(
            data_dir = config.data_dir,
        )
    )

    unicorn = UnicornDashboardApp(
        UnicornDashboardSettings(
            device_settings = config.unicorn_settings
        )
    )

    injector = SignalInjector(
        SignalInjectorSettings(
            time_dim = 'time',
            mixing_seed = 0xDEADBEEF
        )
    )

    freq_map = FrequencyMapper(
        FrequencyMapperSettings(
            mapping = {
                #'GO': 15.0 # Hz
            }
        )
    )

    cat = CuedActionTaskApp(
        TaskSettings(
            data_dir = config.data_dir,
            buffer_dur = 10.0
        )
    )

    preproc = TemporalPreproc(
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

    gadget_config = GadgetConfig()
    hid_units = hid_devices(gadget_config)

    ez.logger.info(f'Accessable HID Devices: {hid_units}')

    app = Application(
        ApplicationSettings(
            port = config.port
        )
    )

    app.panels = {
        'system': system.app,
        'device': unicorn.app,
        'cued_action_task': cat.app,
    }

    components = dict(
        SYSTEM = system,
        UNICORN = unicorn,
        INJECTOR = injector,
        FREQ_MAP = freq_map,
        PREPROC = preproc,
        CAT = cat,
        APP = app,
        **hid_units
    )

    connections = [
        (unicorn.OUTPUT_ACCELEROMETER, ACCELEROMETER_TOPIC),
        (unicorn.OUTPUT_GYROSCOPE, GYROSCOPE_TOPIC),
        (unicorn.OUTPUT_SIGNAL, injector.INPUT_SIGNAL),
        (injector.OUTPUT_SIGNAL, EPHYS_TOPIC),
        (EPHYS_TOPIC, preproc.INPUT_SIGNAL),
        (preproc.OUTPUT_SIGNAL, EPHYS_PREPROC_TOPIC),
        (EPHYS_PREPROC_TOPIC, cat.INPUT_SIGNAL),
        (cat.OUTPUT_SAMPLE, TRIAL_TOPIC),
        (cat.OUTPUT_TARGET_CLASS, TARGET_TOPIC),
        (TARGET_TOPIC, freq_map.INPUT_CLASS),
        (freq_map.OUTPUT_FREQUENCY, injector.INPUT_FREQUENCY),
    ]

    if FBCSP:
        decoding = Dashboard( 
            DashboardSettings(
                data_dir = config.data_dir,
            ) 
        )

        app.panels['decoding'] = decoding.app
        components['DECODING'] = decoding
        connections.extend([
            (EPHYS_PREPROC_TOPIC, decoding.INPUT_SIGNAL),
            (decoding.OUTPUT_DECODE, DECODE_TOPIC),
            (decoding.OUTPUT_CLASS, CLASS_TOPIC),
        ])

    ez.run(
        components = components,
        connections = connections,
        # We're pretty memory constrained on some Pi platforms,
        # multiprocessing may really help us, but the memory hit is
        # substantial.  
        # `import torch` uses ~100MB of memory per-process
        # `import panel` uses ~61MB of memory per-process
        # The pizero2w only has 512 MB of system memory..
        force_single_process = True,
        graph_address = config.graph_address,
    )