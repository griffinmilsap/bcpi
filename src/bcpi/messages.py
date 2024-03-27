from dataclasses import dataclass

@dataclass
class StimMessage:
    value: int = 0

    @classmethod
    def deserialize(cls, data: bytes) -> "StimMessage":
        val = int.from_bytes(data)
        return cls(val)
    
    def serialize(self) -> bytes:
        return int.to_bytes(self.value)