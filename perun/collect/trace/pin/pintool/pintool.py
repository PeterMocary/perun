from jinja2 import Environment, PackageLoader, select_autoescape
from perun.utils.exceptions import InvalidParameterException
from os import environ

env = Environment(
    loader=PackageLoader('perun', package_path='collect/trace/pin/pintool/templates'),
    autoescape=select_autoescape()
)


def assemble_pintool(pintool_file, makefile, function_table=None, collect_args=False, collect_bbls=False, probed=False):
    """ Creates makefile for pintool and the pintool it self from Jinja2 templates.

    :param str pintool_file: path to file where pintool source should be written
    :param str makefile: path to file where makefile rules should be written
    :param dict function_table: representation of function containing their names and arguments indexes and types
    :param bool collect_args: if Ture pintool will be able to collect arguments specified in function_table
    :param bool collect_bbls: if True pintool will be able to collect basic block run-times
                              (can't be used when in probed mode)
    :param bool probed: if True the pintool will instrument using probes instead of just in time compiler
    """
    if probed and collect_bbls:
        raise InvalidParameterException("collect_basic_blocks", True, "Can't be used when Probed mode is enabled.")

    func_names_in_string = ''
    func_len = 0
    if function_table:
        function_names = [*function_table]
        for index, function_name in enumerate(function_names):
            function_names[index] = "\"" + function_name + "\""
        func_names_in_string = ', '.join(function_names)
        func_len = len(function_table)

    PIN_ROOT = environ['PIN_ROOT']

    source_code = env.get_template('pintool.jinja2').render({'probed': probed, 'bbl': collect_bbls, 'collect_arguments': collect_args,
                                                             'function_table': function_table,
                                                             'func_names': func_names_in_string,
                                                             'function_table_len': func_len
                                                             })
    makefile_rules = env.get_template('makefile.jinja2').render({
                                'pin_root': PIN_ROOT})

    with open(pintool_file, 'w') as pt, open(makefile, 'w') as mf:
        pt.write(source_code)
        mf.write(makefile_rules)