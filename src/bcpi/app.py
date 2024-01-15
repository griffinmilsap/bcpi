import typing
from pathlib import Path

import ezmsg.core as ez
from ezmsg.panel.application import Application, ApplicationSettings
from ezmsg.panel.tabbedapp import TabbedApp, Tab
from ezmsg.unicorn.dashboard import UnicornDashboard, UnicornDashboardSettings
from ezmsg.tasks.task import TaskSettings
from ezmsg.tasks.cuedactiontask import CuedActionTask
from ezmsg.tasks.frequencymapper import FrequencyMapper, FrequencyMapperSettings
from ezmsg.gadget.hiddevice import hid_devices
from ezmsg.gadget.config import GadgetConfig

from ezmsg.sigproc.butterworthfilter import ButterworthFilterSettings
from ezmsg.sigproc.decimate import DownsampleSettings
from ezmsg.sigproc.signalinjector import SignalInjector, SignalInjectorSettings

from ezmsg.fbcsp.inference import Inference, InferenceSettings
from ezmsg.fbcsp.dashboard.inferencetab import InferenceTab, InferenceTabSettings
from ezmsg.fbcsp.dashboard.datasettab import DatasetTab, DatasetTabSettings
from ezmsg.fbcsp.dashboard.trainingtab import TrainingTab, TrainingTabSettings
from ezmsg.fbcsp.fbcsptrainprocess import FBCSPTrainProcess

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


class BCPISystemSettings(ez.Settings):
    config_path: typing.Optional[Path] = None

class BCPISystem(ez.Collection, TabbedApp):
    SETTINGS: BCPISystemSettings

    SYSTEM_TAB = SystemTab()
    UNICORN_TAB = UnicornDashboard()
    INJECTOR = SignalInjector()
    MAPPER = FrequencyMapper()
    CAT_TAB = CuedActionTask()
    PREPROC = TemporalPreproc()

    DATASET_TAB = DatasetTab()
    TRAINING_TAB = TrainingTab()
    INFERENCE_TAB = InferenceTab()
    INFERENCE = Inference()
    TRAINING = FBCSPTrainProcess()

    @property
    def title(self) -> str:
        return 'BCPI'
    
    @property
    def tabs(self) -> typing.List[Tab]:
        return [
            self.UNICORN_TAB,
            self.CAT_TAB,
            self.DATASET_TAB,
            self.TRAINING_TAB,
            self.INFERENCE_TAB,
            self.SYSTEM_TAB,
        ]

    def configure(self) -> None:
        config = BCPIConfig(self.SETTINGS.config_path)

        self.SYSTEM_TAB.apply_settings(
            SystemTabSettings(
                data_dir = config.data_dir,
            )
        )

        self.UNICORN_TAB.apply_settings(
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
                    #'GO': 15.0 # Hz
                }
            )
        )

        self.CAT_TAB.apply_settings(
            TaskSettings(
                data_dir = config.data_dir,
                buffer_dur = 10.0
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

        self.INFERENCE_TAB.apply_settings(
            InferenceTabSettings(
                data_dir = config.data_dir
            )
        )

        self.DATASET_TAB.apply_settings(
            DatasetTabSettings(
                data_dir = config.data_dir
            )
        )

        self.TRAINING_TAB.apply_settings(
            TrainingTabSettings(
                data_dir = config.data_dir
            )
        )

    def network(self) -> ez.NetworkDefinition:
        return (
            (self.UNICORN_TAB.OUTPUT_ACCELEROMETER, ACCELEROMETER_TOPIC),
            (self.UNICORN_TAB.OUTPUT_GYROSCOPE, GYROSCOPE_TOPIC),
            (self.UNICORN_TAB.OUTPUT_SIGNAL, self.INJECTOR.INPUT_SIGNAL),
            (self.INJECTOR.OUTPUT_SIGNAL, EPHYS_TOPIC),
            (EPHYS_TOPIC, self.PREPROC.INPUT_SIGNAL),
            (self.PREPROC.OUTPUT_SIGNAL, EPHYS_PREPROC_TOPIC),
            (EPHYS_PREPROC_TOPIC, self.CAT_TAB.INPUT_SIGNAL),
            (self.CAT_TAB.OUTPUT_SAMPLE, TRIAL_TOPIC),
            (self.CAT_TAB.OUTPUT_TARGET_CLASS, TARGET_TOPIC),
            (TARGET_TOPIC, self.MAPPER.INPUT_CLASS),
            (self.MAPPER.OUTPUT_FREQUENCY, self.INJECTOR.INPUT_FREQUENCY),
            (EPHYS_PREPROC_TOPIC, self.INFERENCE.INPUT_SIGNAL),
            (self.INFERENCE_TAB.OUTPUT_SETTINGS, self.INFERENCE.INPUT_SETTINGS),
            (self.INFERENCE.OUTPUT_DECODE, DECODE_TOPIC),
            (self.INFERENCE.OUTPUT_CLASS, CLASS_TOPIC),

            (self.DATASET_TAB.OUTPUT_DATASET, self.TRAINING_TAB.INPUT_DATASET),
            (self.TRAINING_TAB.OUTPUT_TRAIN, self.TRAINING.INPUT_TRAIN),
            (self.TRAINING.OUTPUT_EPOCH, self.TRAINING_TAB.INPUT_EPOCH),
        )


def core_system(config_path: typing.Optional[Path] = None) -> None:

    config = BCPIConfig(config_path = config_path)

    system = BCPISystem(
        BCPISystemSettings(
            config_path = config_path
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
        'bcpi': system.app,
    }

    components = dict(
        SYSTEM = system,
        APP = app,
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