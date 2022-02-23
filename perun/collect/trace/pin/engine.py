""" The SystemTap engine implementation.
"""

import perun.collect.trace.collect_engine as engine
from perun.utils.log import quiet_info, msg_to_stdout
#import perun.utils as utils
#from perun.utils.helpers import SuppressedExceptions
from perun.profile.factory import Profile
from perun.collect.trace.values import check



class PinEngine(engine.CollectEngine):
    """ The Pin engine class, derived from the base CollectEngine.
    """
    name = 'pin'

    def __init__(self, config):
        """ Constructs the engine object.

        :param Configuration config: the collection parameters stored in the configuration object
        """
        super().__init__(config)
        self.program = self._assemble_file_name('./gitpintool', '.cpp')
        self.data = self._assemble_file_name('data', '.txt')

        super()._create_collect_files([self.program, self.data])

    def check_dependencies(self):
        """ Check that the specific dependencies for a given engine are satisfied.
        """
        msg_to_stdout('[Info]: Checking dependencies.', 2)

        # TODO Verify the installation of the pin
        #       $PIN_ROOT vs $PATH

        check(['pin', 'g++'])

        # TODO check the architecture of the processor?
        # Check OS -> check Architecture (lscpu on linux)






    def available_usdt(self, **kwargs):
        """ List the available USDT probes within the given binary files and libraries using
        an engine-specific approach.

        :param kwargs: the required parameters
r
        :return dict: a list of the USDT probe names per binary file
        """
        msg_to_stdout('[Info]: Searching for available USDT probes.',2)
        return {}

    def assemble_collect_program(self, **kwargs):
        """ Assemble the collection program that specifies the probes and the handlers, if needed.

        :param kwargs: the required parameters
        """

        msg_to_stdout('[Info]: Assebling the pintool.',2)

    def collect(self, **kwargs):
        """ Collect the raw performance data using the assembled collection program and other
        parameters.

        :param kwargs: the required parameters
        """
        msg_to_stdout('[Info]: Collecting the performance data.',2)

    def transform(self, **kwargs):
        """ Transform the raw performance data into a resources as used in the profiles.

        :param kwargs: the required parameters

        :return iterable: a generator object that produces the resources
        """
        msg_to_stdout('[Info]: Transforming the collected data to perun profile.',2)
        return Profile()


    def cleanup(self, **kwargs):
        """ Cleans up all the engine-related resources such as files, processes, locks, etc.

        :param kwargs: the required parameters
        """
        msg_to_stdout('[Info]: Cleaning up.',2)









