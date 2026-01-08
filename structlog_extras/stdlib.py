import logging
from abc import ABC
from collections.abc import Callable, Collection
from io import TextIOBase
from typing import BinaryIO, TextIO, cast, final

import structlog
from structlog.typing import EventDict, Processor, ProcessorReturnValue

__all__ = [
    "merge_contextvars_to_record",
    "remove_processors_meta",
    "StructlogForwarder",
    "ProcessorStreamHandler"
]


def merge_contextvars_to_record(record: logging.LogRecord) -> bool:
    """
    Logging filter, to enrich the log record with the contextvars from structlog.
    """
    for var_name, val in structlog.contextvars.get_contextvars().items():
        if var_name in record.__dict__:
            continue
        record.__dict__[var_name] = val
    return True


def remove_processors_meta(_, __, event_dict: EventDict) -> EventDict:
    event_dict.pop("_from_structlog", None)
    event_dict.pop("_record", None)
    return event_dict


class ProcessorHandler(logging.Handler, ABC):
    def __init__(
        self,
        processors: Collection[Processor] = (),
        *,
        use_get_message: bool = True,
        pass_foreign_args: bool = False,
        level: int = logging.NOTSET,
    ):
        super().__init__(level)
        self.processors: Collection[Processor] = processors
        self.use_get_message = use_get_message
        self.pass_foreign_args = pass_foreign_args

    def format(self, record: logging.LogRecord) -> str:
        if formatter := self.formatter:
            return formatter.format(record)
        return record.getMessage() if self.use_get_message else str(record.msg)

    def process(self, record: logging.LogRecord) -> ProcessorReturnValue:
        logger = None
        method_name = record.levelname.lower()
        ed: EventDict = {
            "event": self.format(record),
            "_record": record,
            "_from_structlog": False,
        }

        if self.pass_foreign_args:
            ed["positional_args"] = record.args

        # Add stack-related attributes to the event dict
        if record.exc_info:
            ed["exc_info"] = record.exc_info
        if record.stack_info:
            ed["stack_info"] = record.stack_info

        for proc in self.processors:
            ed = cast(EventDict, proc(logger, method_name, ed))

        return ed

    def handle(self, record: logging.LogRecord) -> bool:
        if self.level > record.levelno:
            return False
        return super().handle(record)


@final
class StructlogForwarder(ProcessorHandler):
    def __init__(
        self,
        pre_chain: Collection[Processor] = (),
        *,
        use_get_message: bool = True,
        pass_foreign_args: bool = False,
        level: int = logging.NOTSET,
    ):
        pre_chain = pre_chain or [
            structlog.stdlib.add_logger_name,
            structlog.stdlib.ExtraAdder(),
            remove_processors_meta,
        ]
        super().__init__(pre_chain, use_get_message=use_get_message, pass_foreign_args=pass_foreign_args, level=level)
        self._logger = structlog.get_logger()
        if hasattr(self._logger, "flush"):
            self.flush = self._logger.flush

    def createLock(self):
        self.lock = None

    def emit(self, record: logging.LogRecord) -> None:
        try:
            event_dict = cast(EventDict, self.process(record))
            event: str = event_dict.pop("event")
            self._logger.log(record.levelno, event, **event_dict)
        except Exception:  # noqa
            self.handleError(record)


@final
class ProcessorStreamHandler(ProcessorHandler):
    """
    Optimized logging.StreamHandler + structlog formatter combo, to allow using binary streams directly.
    """

    def __init__(
        self,
        stream: TextIO | BinaryIO,
        processors: Collection[Processor] = (),
        *,
        use_get_message: bool = True,
        pass_foreign_args: bool = False,
        level: int = logging.NOTSET,
    ):
        super().__init__(processors, use_get_message=use_get_message, pass_foreign_args=pass_foreign_args, level=level)
        self._stream_write: Callable[[str | bytes], int] = stream.write  # type: ignore[assignment]
        self._stream_flush = stream.flush if hasattr(stream, "flush") else lambda: None
        self.terminator = "\n" if isinstance(stream, TextIOBase) else b"\n"

    def emit(self, record: logging.LogRecord) -> None:
        try:
            rendered: str | bytes = self.process(record)  # type: ignore[assignment]
            log_line: str | bytes = rendered + self.terminator  # type: ignore[assignment]
            self._stream_write(log_line)
            self._stream_flush()
        except Exception:  # noqa
            self.handleError(record)

    def flush(self) -> None:
        if self.lock:
            with self.lock:
                self._stream_flush()
        else:
            self._stream_flush()
