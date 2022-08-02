from typing import Optional


def format_bank_card(number: Optional[int]) -> str:
    """
    Format bank card number.
    """
    if number is None:
        return "EB-????"
    return "EB-" + "0" * (4 - len(str(number))) + str(number)
