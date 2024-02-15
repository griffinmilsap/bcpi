class BCPITopics:
    EPHYS = 'EPHYS' # AxisArray -- Electrophysiology
    EPHYS_PREPROC = 'EPHYS_PREPROC' # AxisArray -- Preprocessed Electrophysiology
    ACCELEROMETER = 'ACCEL' # AxisArray -- Accelerometer timeseries from device
    GYROSCOPE = 'GYRO' # AxisArray -- Gyroscope timeseries from device
    DECODE = 'DECODE' # ClassDecodeMessage -- Posterior Decoder Probabilities
    CLASS = 'CLASS' # typing.Optional[str] -- Decoded class
    CAT_TARGET = 'CAT_TARGET' # typing.Optional[str] -- Target class (from CAT)
    CAT_TRIAL = 'CAT_TRIAL' # SampleMessage -- Clipped trial data (Preprocessed) for CAT
    SSVEP_TRIAL = 'SSVEP_TRIAL' # SampleMessage -- Clipped trial data (Preprocessed) for SSVEP


    @classmethod
    def device(cls, name: str) -> str:
        return f'{name}/INPUT_HID'