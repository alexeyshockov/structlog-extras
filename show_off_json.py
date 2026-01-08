import logging

import structlog
from structlog.contextvars import bound_contextvars
from structlog.typing import FilteringBoundLogger


def configure():
    import orjson
    from structlog.processors import CallsiteParameter as CsParam

    from structlog_extras.stdlib import StructlogForwarder

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.CallsiteParameterAdder(
                {CsParam.FILENAME, CsParam.LINENO, CsParam.MODULE, CsParam.FUNC_NAME}
            ),
            structlog.processors.JSONRenderer(orjson.dumps),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
        logger_factory=structlog.BytesLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    root_logger = logging.getLogger()
    root_logger.addHandler(StructlogForwarder())
    root_logger.setLevel(logging.NOTSET)


def main():
    logging.getLogger("our.app").info("Hello, World!")

    structured_logger: FilteringBoundLogger = structlog.get_logger()
    structured_logger.info("Hello from structlog!", some_key="some_value")

    with bound_contextvars(another_key="another_value"):
        # Context vars are merged even when using the standard logging module
        logging.getLogger("our.app").info("Hello again!")


if __name__ == "__main__":
    configure()
    main()
