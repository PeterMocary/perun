def get_func_table():
    """ Returns table of function with arguments, which should be collected by pintool

    NOTE: for now just dummy table for sorts
    """
    return {
        'QuickSort': {'1': 'int'},
        'QuickSortBad': {'1': 'int'},
        'Partition': {'1': 'int', '2': 'int'},
        'BadPartition': {'1': 'int', '2': 'int'},
        'InsertSort': {'1': 'int'},
        'HeapSort': {'1': 'int'},
        'repairTop': {'1': 'int', '2': 'int'},
        'swap': {'1': 'int', '2': 'int'}
    }

def get_func_names_in_string():
    """ Creates a string from function names in quotes. Auxiliary function for generating pintool code.

    :return str:  String with format: "<func-name>", "<func-name>", ...
    """
    function_names = [*get_func_table()]
    for index, function_name in enumerate(function_names):
        function_names[index] = "\"" + function_name + "\""
    return ', '.join(function_names)