from jinja2 import Environment, PackageLoader, select_autoescape
from perun.utils.log import quiet_info, msg_to_stdout
from perun.collect.trace.pin.scan_binary import get_func_table, get_func_names_in_string

env = Environment(
    loader=PackageLoader('perun', package_path='collect/trace/pin/pintool/templates'),
    autoescape=select_autoescape()
)

def assemble_pintool(pintool_file, makefile):
    """ Creates makefile for pintool and the pintool it self from Jinja2 templates.

    :param str pintool_file: path to file where pintool source should be written
    :param str makefile: path to file where makefile rules should be written
    """
    func_table = get_func_table()
    source_code = env.get_template('pintool.jinja2').render({'probed': False, 'bbl': False, 'collect_arguments': False,
                                                             'function_table': func_table,
                                                             'get_func_names': get_func_names_in_string,
                                                             'function_table_len': len(func_table)
                                                             })
    makefile_rules = env.get_template('makefile.jinja2').render({'pin_root': '/home/ptr/Work/VUT/3BIT/bp/develop/pin-3.21-98484-ge7cd811fd-gcc-linux'})

    with open(pintool_file, 'w') as pt, open(makefile, 'w') as mf:
        pt.write(source_code)
        mf.write(makefile_rules)

#TODO: remove routineInfo (There is a problem with passing string) or delete the allocated structures
#TODO: add switches to commandline
#TODO: figure out the double
#TODO: better generated pintool formating