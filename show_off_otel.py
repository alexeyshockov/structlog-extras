import logging

import structlog
import structlog_extras.stdlib
from dotenv import load_dotenv
from structlog.contextvars import bound_contextvars
from structlog.typing import FilteringBoundLogger


# noinspection PyProtectedMember
def configure_otel():
    """
    See also the official examples:
     - https://github.com/open-telemetry/opentelemetry-python/blob/v1.30.0/docs/examples/logs/example.py
    """
    from opentelemetry._logs import set_logger_provider
    from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

    logger_provider = LoggerProvider()
    set_logger_provider(logger_provider)
    exporter = OTLPLogExporter()
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))

    # Add OTEL as another handler to the root logger
    logging.getLogger().addHandler(LoggingHandler())


def main():
    logging.getLogger("our.app").info("Hello, World!")

    structured_logger: FilteringBoundLogger = structlog.get_logger("our.app")
    structured_logger.info("Hello from structlog!", some_key="some_value")

    with bound_contextvars(another_key="another_value"):
        # Context vars are merged even when using the standard logging module
        logging.getLogger("our.app").info("Hello again!")


if __name__ == "__main__":
    load_dotenv()
    structlog_extras.presets.stdlib_json(logging.NOTSET)
    configure_otel()
    main()
