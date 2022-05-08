from elftools.elf.elffile import ELFFile
from elftools.common.py3compat import bytes2str
from elftools.dwarf.die import DIE

from perun.utils.exceptions import InvalidBinaryException, PinBinnaryScanUnsuccessful


def process_file(filename: str) -> dict:
    """ Read DWARF info from file and extract information about functions from it.
        :param str filename: binary with DWARF debug info one wants to analyse
        :return dict: dictionary with names and parameter types of functions
    """
    with open(filename, 'rb') as f:
        elffile = ELFFile(f)

        if not elffile.has_dwarf_info():
            # File has no DWARF info
            raise InvalidBinaryException

        dwarfinfo = elffile.get_dwarf_info()

        func_table = {}
        for CU in dwarfinfo.iter_CUs():
            # Start with the top DIE, the root for this CU's DIE tree
            try:
                top_DIE = CU.get_top_DIE()
            except Exception:
                raise PinBinnaryScanUnsuccessful

            # print('name=%s' % top_DIE.get_full_path())
            die_func_info(top_DIE, func_table)
    return func_table


def die_func_info(die, func_table: dict):
    """ Gather information about functions. Particularly their names, argument types and indexes.

        :param DIE die: the debugging information entry from which one wants to extract information about functions
        :param dict func_table: dictionary to which are the information appended
    """
    for child in die.iter_children():
        if child.tag == 'DW_TAG_subprogram':
            function_name_attribute = child.attributes['DW_AT_name']
            function_name = bytes2str(function_name_attribute.value)

            parameters = {}
            param_index = -1
            for subprogram_child in child.iter_children():
                if subprogram_child.tag == 'DW_TAG_formal_parameter':
                    param_index += 1
                    type_die = subprogram_child.get_DIE_from_attribute('DW_AT_type')
                    type_in_str = get_type_str(type_die)
                    if not type_in_str:
                        continue

                    try:
                        arg_name = bytes2str(subprogram_child.attributes['DW_AT_name'].value)
                    except KeyError:
                        arg_name = 'No name in DWARF'

                    parameters[str(param_index)] = (type_in_str, arg_name)

            if parameters != {}:
                func_table[function_name] = parameters


def get_type_str(type_die):
    """ Extracts type from dwarf format to string.
        :param DIE type_die: debugging information entry containing information about type
        :return: type in str or None if the type isn't one of selected types
    """

    supported_basic_types = ["int", "char", "float", "double", "_Bool"]
    if type_die.tag == 'DW_TAG_base_type':
        type_str = bytes2str(type_die.attributes['DW_AT_name'].value)
        for supported_basic_type in supported_basic_types:
            if supported_basic_type in type_str:
                return type_str
        return None

    elif type_die.tag == 'DW_TAG_pointer_type':
        if 'DW_AT_type' in type_die.attributes:
            type_die = type_die.get_DIE_from_attribute('DW_AT_type')
            type = get_type_str(type_die)
            if type == 'char':
                return 'char *'
            else:
                return None
        else:
            # pointer without type?
            return None

    elif type_die.tag == 'DW_TAG_const_type':
        try:
            type_die = type_die.get_DIE_from_attribute('DW_AT_type')
        except KeyError:
            return None
        type_str = bytes2str(type_die.attributes['DW_AT_name'].value)

        for supported_basic_type in supported_basic_types:
            if supported_basic_type in type_str:
                return 'const ' + type_str
        return None
    else:
        return None
