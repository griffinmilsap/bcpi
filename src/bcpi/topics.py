class BCPITopics:
    EPHYS = 'EPHYS' # AxisArray -- Electrophysiology
    EPHYS_PREPROC = 'EPHYS_PREPROC' # AxisArray -- Preprocessed Electrophysiology
    ACCELEROMETER = 'ACCEL' # AxisArray -- Accelerometer timeseries from device
    GYROSCOPE = 'GYRO' # AxisArray -- Gyroscope timeseries from device
    DECODE = 'DECODE' # ClassDecodeMessage -- Posterior Decoder Probabilities
    CLASS = 'CLASS' # typing.Optional[str] -- Decoded class
    TARGET = 'TARGET' # typing.Optional[str] -- Target class (from Task)
    TRIAL = 'TRIAL' # SampleMessage -- Clipped trial data (Preprocessed)

    @classmethod
    def device(cls, name: str) -> str:
        return f'{name}/INPUT_HID'