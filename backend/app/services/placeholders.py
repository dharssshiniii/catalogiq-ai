PLACEHOLDERS = {"", "-", "-- unbranded --", "-- no unilog brand --", "-- no dib brand --"}


def is_placeholder(value: object) -> bool:
    if value is None:
        return True
    return str(value).strip().casefold() in PLACEHOLDERS

