import logging

import structlog
from dotenv import load_dotenv
from structlog.contextvars import bound_contextvars
from structlog.typing import FilteringBoundLogger

import structlog_extras


def main():
    logging.getLogger("our.app").info("Hello, World!")

    structured_logger: FilteringBoundLogger = structlog.get_logger()
    structured_logger.info("Hello from structlog!", some_key="some_value")

    with bound_contextvars(another_key="another_value"):
        # Context vars are merged even when using the standard logging module
        logging.getLogger("our.app").info("Hello again!", extra={"some_stdlib_key": "some_stdlib_value"})


if __name__ == "__main__":
    load_dotenv()
    structlog_extras.presets.stdlib_json(logging.NOTSET)
    main()
