def empty(input):
    return input is None or input == ''


def not_empty(input):
    return not empty(input)


def join_all(input_list):
    if input_list is None:
        return ''
    return ''.join(input_list)


def molecular_formula_of(input_molecule):
    """
    input_molecule: pass molecule as simple string such as H20 to get it back in proper chemical notation
    """
    subscript = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
    return input_molecule.translate(subscript)


def not_numeric(input_value):
    return not numeric(input_value)


def numeric(input_value):
    if isinstance(input_value, (int, float)):
        return True
    if _pieces_are_numeric(input_value, '.') or _pieces_are_numeric(input_value, ','):
        return True
    return False


def _pieces_are_numeric(input_value, separator):
    pieces = input_value.split(separator)
    if len(pieces) == 1:
        return input_value.isnumeric()
    if len(pieces) == 2:
        return pieces[0].isnumeric() and pieces[1].isnumeric()
    return False

