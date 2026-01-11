import logging
from sys import stdout
from typing import TextIO

import structlog
from structlog.processors import CallsiteParameter as CsParam

from ._proc import drop_uvicorn_color_message
from .stdlib import merge_contextvars_to_record, ProcessorStreamHandler, remove_processors_meta


__all__ = ["stdlib_dev_console", "stdlib_json"]


def stdlib_json(min_log_level: int = logging.INFO) -> None:
    """
    Forward structlog to stdlib, output every log record as a JSON line to the console (stdout).

    Useful in cases you want to use other integrations (OpenTelemetry SDK, Sentry SDK, etc.), which support stdlib
    logging out of the box.

    Optimized for remote deployments.
    """
    root_logger = logging.getLogger()
    # Add context (bound) vars to all log records, not only structlog ones
    root_logger.addFilter(merge_contextvars_to_record)
    root_logger.setLevel(min_log_level)

    def json_renderer():
        try:
            import orjson

            return stdout.buffer, structlog.processors.JSONRenderer(orjson.dumps)
        except ImportError:
            return stdout, structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            structlog.stdlib.render_to_log_args_and_kwargs
        ],
        wrapper_class=structlog.make_filtering_bound_logger(min_log_level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    stream, renderer = json_renderer()
    handler = ProcessorStreamHandler(stream, [
        structlog.stdlib.add_logger_name,
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.ExtraAdder(),
        drop_uvicorn_color_message,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        remove_processors_meta,
        renderer,
    ])

    root_logger.addHandler(handler)


def stdlib_dev_console(
    min_log_level: int = logging.INFO,
    stream: TextIO = stdout,
    renderer: structlog.dev.ConsoleRenderer | None = None,
) -> None:
    """
    Forward structlog to stdlib, output to stdout using structlog.dev.ConsoleRenderer.

    Optimized for local development.
    """
    root_logger = logging.getLogger()
    # Add context (bound) vars to all log records, not only structlog ones
    root_logger.addFilter(merge_contextvars_to_record)
    root_logger.setLevel(min_log_level)

    structlog.configure(
        processors=[
            structlog.stdlib.render_to_log_args_and_kwargs
        ],
        wrapper_class=structlog.make_filtering_bound_logger(min_log_level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    handler = ProcessorStreamHandler(stream, [
        structlog.stdlib.add_logger_name,
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.ExtraAdder(),
        drop_uvicorn_color_message,
        # Just time, date is useless when running/developing locally
        structlog.processors.TimeStamper(fmt="%H:%M:%S.%f"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.CallsiteParameterAdder(
            {CsParam.FILENAME, CsParam.LINENO, CsParam.MODULE, CsParam.FUNC_NAME}
        ),
        remove_processors_meta,
        renderer or structlog.dev.ConsoleRenderer(),
    ])

    root_logger.addHandler(handler)
