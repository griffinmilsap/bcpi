import typing
from pathlib import Path

import ezmsg.core as ez
from ezmsg.panel.tabbedapp import TabbedApp, Tab
from ezmsg.tasks.task import TaskSettings
from ezmsg.tasks.cuedactiontask import CuedActionTask
from ezmsg.tasks.ssvep.task import SSVEPTask

from ezmsg.fbcsp.dashboard.inferencetab import InferenceTab, InferenceTabSettings
from ezmsg.fbcsp.dashboard.datasettab import DatasetTab, DatasetTabSettings
from ezmsg.fbcsp.dashboard.trainingtab import TrainingTab, TrainingTabSettings
from ezmsg.fbcsp.fbcsptrainprocess import FBCSPTrainProcess

from .config import BCPIConfig
from .core import BCPICore, BCPICoreSettings, BCPITopics


class BCPISettings(ez.Settings):
    config_path: typing.Optional[Path] = None

class BCPI(ez.Collection, TabbedApp):
    SETTINGS: BCPISettings

    CORE = BCPICore()
    CAT_TAB = CuedActionTask()
    SSVEP_TAB = SSVEPTask()

    DATASET_TAB = DatasetTab()
    TRAINING_TAB = TrainingTab()
    INFERENCE_TAB = InferenceTab()
    TRAINING = FBCSPTrainProcess()

    @property
    def title(self) -> str:
        return 'BCPI - BCI Development Environment for Raspberry Pi'
    
    @property
    def tabs(self) -> typing.List[Tab]:
        return [
            self.CORE.UNICORN,
            self.CAT_TAB,
            self.SSVEP_TAB,
            self.DATASET_TAB,
            self.TRAINING_TAB,
            self.INFERENCE_TAB,
            self.CORE.SYSTEM_TAB,
        ]

    def configure(self) -> None:
        config = BCPIConfig(self.SETTINGS.config_path)

        self.CORE.apply_settings(
            BCPICoreSettings(
                config_path = self.SETTINGS.config_path
            )
        )

        task_settings = TaskSettings(
            data_dir = config.data_dir,
            buffer_dur = 10.0
        )

        self.CAT_TAB.apply_settings(task_settings)
        self.SSVEP_TAB.apply_settings(task_settings)

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
            (BCPITopics.EPHYS_PREPROC, self.CAT_TAB.INPUT_SIGNAL),
            (self.CAT_TAB.OUTPUT_SAMPLE, BCPITopics.CAT_TRIAL),
            (self.CAT_TAB.OUTPUT_TARGET_CLASS, BCPITopics.CAT_TARGET),

            (BCPITopics.EPHYS_PREPROC, self.SSVEP_TAB.INPUT_SIGNAL),
            (self.SSVEP_TAB.OUTPUT_SAMPLE, BCPITopics.SSVEP_TRIAL),

            (self.INFERENCE_TAB.OUTPUT_SETTINGS, self.CORE.INPUT_INFERENCE_SETTINGS),
            (BCPITopics.DECODE, self.INFERENCE_TAB.INPUT_DECODE),
            (BCPITopics.CLASS, self.INFERENCE_TAB.INPUT_CLASS),

            (self.DATASET_TAB.OUTPUT_DATASET, self.TRAINING_TAB.INPUT_DATASET),
            (self.TRAINING_TAB.OUTPUT_TRAIN, self.TRAINING.INPUT_TRAIN),
            (self.TRAINING.OUTPUT_EPOCH, self.TRAINING_TAB.INPUT_EPOCH),
        )
