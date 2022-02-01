from typing import Type


def get_import_full_name(subject: Type) -> str:
    if hasattr(subject, "__name__"):
        return ".".join([subject.__module__, subject.__name__])
    return ".".join([subject.__module__, subject.__class__.__name__])
