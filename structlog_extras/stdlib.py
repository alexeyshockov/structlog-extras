import logging
from collections.abc import Collection
from typing import cast, final

import structlog
from structlog.typing import EventDict, Processor

__all__ = ["StructlogHandler", "attach_contextvars", "pass_to_logger"]

_LOG_RECORD_KEYS = logging.makeLogRecord({}).__dict__.keys()


def pass_to_logger(_, __, event_dict: EventDict) -> tuple[tuple[str], dict[str, object]]:
    event = event_dict.pop("event")
    extra = {k: v for k, v in event_dict.items() if k not in _LOG_RECORD_KEYS}
    return (event,), {"extra": extra}


def attach_contextvars(record: logging.LogRecord) -> bool:
    for var_name, val in structlog.contextvars.get_contextvars().items():
        if var_name in record.__dict__:
            continue
        record.__dict__[var_name] = val
    return True


@final
class StructlogHandler(logging.Handler):
    def __init__(
        self,
        pre_chain: Collection[Processor] = (),
        *,
        use_get_message: bool = True,
        pass_foreign_args: bool = False,
        level: int = logging.NOTSET,
    ):
        super().__init__(level)
        self.processors: Collection[Processor] = pre_chain or [
            structlog.stdlib.add_logger_name,
            structlog.stdlib.ExtraAdder(),
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
        ]
        self.use_get_message = use_get_message
        self.pass_foreign_args = pass_foreign_args
        self._logger = structlog.get_logger()

    def format(self, record: logging.LogRecord) -> str:
        if formatter := self.formatter:
            return formatter.format(record)
        return record.getMessage() if self.use_get_message else str(record.msg)

    def process(self, record: logging.LogRecord) -> EventDict:
        logger = None
        meth_name = record.levelname.lower()
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

        for proc in self.processors or ():
            ed = cast(EventDict, proc(logger, meth_name, ed))

        return ed

    def handle(self, record: logging.LogRecord) -> None:
        if self.level > record.levelno:
            return
        super().handle(record)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            event_dict = self.process(record)
            event: str = event_dict.pop("event")
            self._logger.log(record.levelno, event, **event_dict)
        except Exception:  # noqa
            self.handleError(record)

    def flush(self) -> None:
        if flush := getattr(self._logger, "flush", None):
            flush()
