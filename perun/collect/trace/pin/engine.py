""" The SystemTap engine implementation.
"""

import perun.collect.trace.collect_engine as engine
from perun.utils.log import msg_to_stdout
from perun.collect.trace.values import check
from perun.collect.trace.pin.pintool import pintool
from perun.logic.pcs import get_tmp_directory
import perun.utils as utils
import perun.collect.trace.pin.parse as parse
import perun.collect.trace.pin.scan_binary as scan_binary
from os import environ
from perun.utils.exceptions import PinUnspecifiedPinRoot


class PinEngine(engine.CollectEngine):
    """ The Pin engine class, derived from the base CollectEngine.
    """
    name = 'pin'

    def __init__(self, config):
        """ Constructs the engine object.

        :param Configuration config: the collection parameters stored in the configuration object
        """
        super().__init__(config)
        self.pintool_src = f'{get_tmp_directory()}/pintool.cpp'
        self.pintool_makefile = f'{get_tmp_directory()}/makefile'
        self.data = self._assemble_file_name('data', '.txt')
        self.function_table = None

        super()._create_collect_files([self.data, self.pintool_src, self.pintool_makefile])

    def check_dependencies(self):
        """ Check that the pin and compiler for pintools are available and if pin's root folder is specified.
        """
        msg_to_stdout('[Info]: Checking dependencies.', 2)
        check(['pin', 'g++'])
        if "PIN_ROOT" not in environ.keys():
            raise PinUnspecifiedPinRoot()

    def available_usdt(self, **kwargs):
        """ This function returns empty dictionary, because USDTs aren't used in pin engine.
        """
        # NOTE: This function isn't needed by pin negine
        return {}

    def assemble_collect_program(self, **kwargs):
        """ Assemble a pintool for the collection based on selected configuration options.

        :param kwargs: the configuration parameters
        """
        if kwargs['collect_arguments']:
            msg_to_stdout('[Info]: Scanning binary for functions and their arguments.', 2)
            self.function_table = scan_binary.process_file(self.binary)

        msg_to_stdout('[Info]: Assebling the pintool.', 2)

        pintool.assemble_pintool(self.pintool_src, self.pintool_makefile, self.function_table,
                                 kwargs['collect_arguments'], kwargs['collect_basic_blocks'], kwargs['probed'])

        utils.run_safely_external_command(f'make -C {get_tmp_directory()}')

    def collect(self, config, **_):
        """ Collect the raw performance data using the assembled pintool.

        :param Configuration config: the configuration object
        """
        msg_to_stdout('[Info]: Collecting the performance data.', 2)
        utils.run_safely_external_command(
            f'pin -t {get_tmp_directory()}/obj-intel64/pintool.so -o {self.data} -- {config.executable}')

    def transform(self, config, **kwargs):
        """ Transform the raw performance data into a resources as used in the profiles.

        :param kwargs: the required parameters

        :return iterable: a generator object that produces the resources
        """
        msg_to_stdout('[Info]: Transforming the collected data to perun profile.', 2)
        return parse.parse_data(self.data, config.executable.workload, self.function_table)

    def cleanup(self, config, **kwargs):
        """ Cleans up all the engine-related resources such as files, processes, locks, etc.

        :param kwargs: the required parameters
        """
        msg_to_stdout('[Info]: Cleaning up.', 2)
        #utils.run_safely_external_command(f'make -C {get_tmp_directory()} clean-obj')
        super()._finalize_collect_files(['data', 'pintool_src', 'pintool_makefile'], config.keep_temps, config.zip_temps)
        utils.run_safely_external_command(f'rm -rf {get_tmp_directory()}/obj-intel64')









