from structlog.typing import EventDict


def drop_uvicorn_color_message(_, __, event_dict: EventDict) -> EventDict:
    if logger_name := event_dict.get("logger"):
        if logger_name.startswith("uvicorn."):
            event_dict.pop("color_message", None)
    return event_dict
