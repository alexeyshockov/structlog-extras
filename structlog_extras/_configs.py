"""
Most common structlog configurations.
"""

import logging

import structlog

from .stdlib import merge_contextvars_to_record, ProcessorStreamHandler, remove_processors_meta


def use_stdlib_json_to_console() -> None:
    """
    Forward structlog to stdlib, output every log record as a JSON line to the console (stdout).
    """
    from sys import stdout

    root_logger = logging.getLogger()
    # Add context (bound) vars to all log records, not only structlog ones
    root_logger.addFilter(merge_contextvars_to_record)
    root_logger.setLevel(logging.INFO)

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
        wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    stream, renderer = json_renderer()
    handler = ProcessorStreamHandler(stream, [
        structlog.stdlib.ExtraAdder(),
        structlog.stdlib.add_logger_name,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        remove_processors_meta,
        renderer,
    ])

    root_logger.addHandler(handler)
