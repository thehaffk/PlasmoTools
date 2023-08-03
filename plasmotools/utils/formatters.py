from typing import Optional


def format_bank_card(number: Optional[int], bank_prefix: str = "EB") -> str:
    """
    Format bank card number.
    """
    if number is None:
        return bank_prefix + "-????"
    return bank_prefix + "-" + "0" * (4 - len(str(number))) + str(number)


def build_progressbar(cursor: int, total_count: int) -> str:
    """
    Build progressbar with given numbers

    :return: string with 🟥 and 🟩
    """
    if total_count < 10:
        cursor *= 10
        total_count *= 10

    if total_count == 0 or total_count == cursor:
        return "🟩" * 10

    return "🟩" * int((cursor // (total_count // 10))) + "🟥" * (
        10 - int((cursor // (total_count // 10)))
    )
