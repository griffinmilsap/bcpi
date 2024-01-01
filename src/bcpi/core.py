import typing
from pathlib import Path

import ezmsg.core as ez
from ezmsg.panel.application import Application, ApplicationSettings
from ezmsg.unicorn.dashboard import UnicornDashboardApp
from ezmsg.tasks.task import TaskSettings
from ezmsg.tasks.directory import TaskDirectory
from ezmsg.gadget.hiddevice import HIDDevice, HIDDeviceSettings

from ezmsg.sigproc.butterworthfilter import ButterworthFilterSettings
from ezmsg.sigproc.decimate import DownsampleSettings
from .temporalpreproc import TemporalPreproc, TemporalPreprocSettings

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

def core_system(data_dir: Path, port: int) -> None:

    unicorn = UnicornDashboardApp()

    tasks = TaskDirectory(
        TaskSettings(
            data_dir = data_dir,
            buffer_dur = 10.0
        )
    )

    preproc = TemporalPreproc(
        TemporalPreprocSettings(
            filt_settings = ButterworthFilterSettings(
                axis = 'time',
                order = 0, # Butterworth filter order
                cuton = None, # Cuton (Hz)
                cutoff = None, # Cutoff (Hz)
            ),
            decimate_settings = DownsampleSettings(
                axis = 'time',
                factor = 1
            ),
            ewm_history_dur = 2.0
        )
    )

    app = Application(
        ApplicationSettings(
            port = port
        )
    )

    app.panels = {
        'device': unicorn.app,
        'tasks': tasks.app,
    }

    components = dict(
        UNICORN = unicorn,
        PREPROC = preproc,
        TASKS = tasks,
        APP = app,
    )

    connections = [
        (unicorn.OUTPUT_ACCELEROMETER, ACCELEROMETER_TOPIC),
        (unicorn.OUTPUT_GYROSCOPE, GYROSCOPE_TOPIC),
        (unicorn.OUTPUT_SIGNAL, EPHYS_TOPIC),
        (EPHYS_TOPIC, preproc.INPUT_SIGNAL),
        (preproc.OUTPUT_SIGNAL, EPHYS_PREPROC_TOPIC),
        (EPHYS_PREPROC_TOPIC, tasks.INPUT_SIGNAL),
        (tasks.OUTPUT_SAMPLE, TRIAL_TOPIC),
        (tasks.OUTPUT_TARGET_CLASS, TARGET_TOPIC),
    ]

    if FBCSP:
        decoding = Dashboard( 
            DashboardSettings(
                data_dir = data_dir,
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
        connections = connections
    )