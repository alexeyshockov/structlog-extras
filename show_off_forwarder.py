import logging

import structlog
from structlog.contextvars import bound_contextvars
from structlog.typing import FilteringBoundLogger


def configure():
    from structlog.processors import CallsiteParameter as CsParam

    from structlog_extras.stdlib import StructlogForwarder

    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.contextvars.merge_contextvars,
            # Just time, date is useless when running/developing locally
            structlog.processors.TimeStamper(fmt="%H:%M:%S.%f"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.CallsiteParameterAdder(
                {CsParam.FILENAME, CsParam.LINENO, CsParam.MODULE, CsParam.FUNC_NAME}
            ),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
        logger_factory=structlog.WriteLoggerFactory(),
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
