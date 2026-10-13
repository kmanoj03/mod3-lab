from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class CheckInventoryRequest(_message.Message):
    __slots__ = ("item_id", "quantity")
    ITEM_ID_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    item_id: str
    quantity: int
    def __init__(self, item_id: _Optional[str] = ..., quantity: _Optional[int] = ...) -> None: ...

class CheckInventoryResponse(_message.Message):
    __slots__ = ("item_id", "requested_quantity", "available_quantity", "available")
    ITEM_ID_FIELD_NUMBER: _ClassVar[int]
    REQUESTED_QUANTITY_FIELD_NUMBER: _ClassVar[int]
    AVAILABLE_QUANTITY_FIELD_NUMBER: _ClassVar[int]
    AVAILABLE_FIELD_NUMBER: _ClassVar[int]
    item_id: str
    requested_quantity: int
    available_quantity: int
    available: bool
    def __init__(self, item_id: _Optional[str] = ..., requested_quantity: _Optional[int] = ..., available_quantity: _Optional[int] = ..., available: _Optional[bool] = ...) -> None: ...
