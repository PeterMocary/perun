import pygccxml
from elftools.elf.elffile import ELFFile
from elftools.common.py3compat import bytes2str
from elftools.dwarf.die import DIE

def process_file(filename: str) -> dict:
    print('Processing file:', filename)
    with open(filename, 'rb') as f:
        elffile = ELFFile(f)

        if not elffile.has_dwarf_info():
            print('  file has no DWARF info')
            #FIXME: add exception
            return

        dwarfinfo = elffile.get_dwarf_info()

        func_table = {}
        for CU in dwarfinfo.iter_CUs():
            # Start with the top DIE, the root for this CU's DIE tree
            top_DIE = CU.get_top_DIE()
            #print('    name=%s' % top_DIE.get_full_path())
            die_func_info(top_DIE, func_table)

    return func_table

def die_func_info(die, func_table: dict):
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
                    type_name = get_type_str(type_die)
                    if not type_name:
                        continue
                    parameters[str(param_index)] = type_name

            if parameters != {}:
                func_table[function_name] = parameters


def get_type_str(type_die):
    if type_die.tag == 'DW_TAG_base_type':
        type_str = bytes2str(type_die.attributes['DW_AT_name'].value)
        if type_str == "wchar_t":
            return None
        return type_str if type_str != "_Bool" else "bool"

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
        return 'const ' + type_str if type_str != "_Bool" else "const bool"

    # elif type_die.tag == "DW_TAG_subroutine_type":
    #     return None
    #
    # elif type_die.tag == 'DW_TAG_reference_type':
    #     # if 'DW_AT_type' in type_die.attributes:
    #     #     type_die = type_die.get_DIE_from_attribute('DW_AT_type')
    #     #     return get_type_str(type_die) + '&'
    #     # else:
    #     #     # reference without type?
    #     #     return None
    #     return None
    #
    # elif type_die.tag == 'DW_TAG_typedef':
    #     return None

    else:
        return None