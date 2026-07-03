def country_flag(country_code: str | None) -> str:
    """ISO 3166-1 alpha-2 kodundan emoji bayrak."""
    if not country_code or len(country_code) != 2:
        return ""
    code = country_code.upper()
    if not code.isalpha():
        return ""
    return "".join(chr(0x1F1E6 + ord(char) - ord("A")) for char in code)
