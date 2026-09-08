FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r", "\n")


def safe_cell(value):
    """Prevent spreadsheet programs from interpreting exported text as a formula."""
    if value is None:
        return ""
    text = str(value)
    if text.startswith(FORMULA_PREFIXES):
        return "'" + text
    return text


def safe_row(values):
    return [safe_cell(value) for value in values]
