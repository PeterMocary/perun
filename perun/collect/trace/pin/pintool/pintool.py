from jinja2 import Environment, PackageLoader, select_autoescape
from perun.utils.log import quiet_info, msg_to_stdout

env = Environment(
    loader=PackageLoader('perun', package_path='collect/trace/pin/pintool/templates'),
    autoescape=select_autoescape()
)

def assemble_pintool(pintool_file, makefile, function_table=None):
    """ Creates makefile for pintool and the pintool it self from Jinja2 templates.

    :param str pintool_file: path to file where pintool source should be written
    :param str makefile: path to file where makefile rules should be written
    :param dict function_table: representation of function containing their names and parameter indexes and types
    """
    func_names_in_string = ''
    if function_table:
        function_names = [*function_table]
        for index, function_name in enumerate(function_names):
            function_names[index] = "\"" + function_name + "\""
        func_names_in_string = ', '.join(function_names)

    source_code = env.get_template('pintool.jinja2').render({'probed': False, 'bbl': False, 'collect_arguments': True,
                                                             'function_table': function_table,
                                                             'func_names': func_names_in_string,
                                                             'function_table_len': len(function_table) if function_table else 0
                                                             })
    makefile_rules = env.get_template('makefile.jinja2').render({'pin_root': '/home/ptr/Work/VUT/3BIT/bp/develop/pin-3.21-98484-ge7cd811fd-gcc-linux'})

    with open(pintool_file, 'w') as pt, open(makefile, 'w') as mf:
        pt.write(source_code)
        mf.write(makefile_rules)

#TODO: remove routineInfo (There is a problem with passing string) or delete the allocated structures
#TODO: add switches to commandline
#TODO: figure out the double
#TODO: better generated pintool formating