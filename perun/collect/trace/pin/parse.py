from perun.profile.factory import Profile
from perun.utils.log import msg_to_stdout
from abc import ABC, abstractmethod
from enum import IntEnum


class Location(IntEnum):
    """ Enum that represents the different locations of collected data. Differentiates the location of entry in the
    output form pin. Before or after the instrumented unit (routine or basic block)
    """
    BEFORE = 0
    AFTER = 1


class Granularity(IntEnum):
    """ Enum that represents the granularity of instrumentation. Differentiates the routines and basic block entries in
    the output form pin.
    """
    RTN = 0
    BBL = 1


class RawDataEntry:
    """ Class that represents single entry (line) from pin output. The entry can contain information about routine or
    basic block.

    :ivar str name: the name of the routine (or routine containing the basic block)
    :ivar int location: determines the location of the data entry (see Location enum)
    :ivar int granularity: determines if the data entry contains routine or basic block information
    :ivar int rtn_id: identification number of the routine (or the routine containing the basic block)
    :ivar int bbl_id: identification number of the basic block (or None if the entry contains data regarding routine)
    :ivar int tid: thread ID of the thread in which routine or basic block were run.
    :ivar int pid: process ID of the process on which the collection was performed.
    :ivar int timestamp: timestamp when was the function or basic block started or finished
                         (based on location of the entry: BEFORE = started and AFTER = finished)
    :ivar dict args: contains arguments if the entry is before routine only and the collection of arguments was
                     specified by the user (otherwise is None)
    """

    # RTN_FORMAT also supports function arguments at the end
    RTN_FORMAT = ["granularity", 'location', 'tid', 'pid', 'timestamp', 'rtn_id', 'name']
    BBL_FORMAT = [*RTN_FORMAT, 'bbl_id']

    def __init__(self, data: dict):
        self.name = data['name']
        self.location = data['location']
        self.granularity = data['granularity']
        self.rtn_id = data['rtn_id']
        self.bbl_id = data['bbl_id'] if self.granularity == Granularity.BBL else None
        self.tid = data['tid']
        self.pid = data['pid']
        self.timestamp = data['timestamp']
        self.args = None

    def time_delta(self, other) -> int:
        """ Calculates the time delta from two entries

        :param RawDataEntry other: the data entry complementary to self
        :return int: time delta of the complementary entries
        """
        # FIXME: Exception when the entries aren't a pair?
        return abs(self.timestamp - other.timestamp)

    def is_located_before(self) -> bool:
        """ Identifies if the data entry is located before instrumentation unit.
        :return bool: True if the entry is from the entrance to the instrumentation unit, otherwise False
        """
        return self.location == Location.BEFORE

    def is_function_granularity(self) -> bool:
        """ Identifies if the data entry is at the function (routine) granularity
        :return bool: True if the granularity of the entry is at routine level, otherwise False
        """
        return self.granularity == Granularity.RTN

    def __eq__(self, other) -> bool:
        """ Determine if two entries are complementary. Two entries are complementary when their location are opposite
        and everything else is the same.
        """
        if self.rtn_id == other.rtn_id and self.bbl_id == other.bbl_id and \
           self.name == other.name and \
           self.tid == other.tid and self.pid == other.pid and \
           self.location != other.location:
            return True
        return False

    def __repr__(self) -> str:
        return f"RAW:\n"                                \
               f"function_name: {self.name}\n"          \
               f"granularity: {self.granularity}\n"     \
               f"location: {self.location}\n"           \
               f"function_id: {self.rtn_id}\n"          \
               f"basic_block_id: {self.bbl_id}\n"       \
               f"tid: {self.tid}\n"                     \
               f"pid: {self.pid}\n"                     \
               f"timestamp: {self.timestamp}\n"


class Record(ABC):
    """ Class that represents 2 paired data entries created by pin. Holds information about run-time of a routine or a
    basic block along with some additional information for deeper analysis.

    :ivar str name: name of the routine (or routine containing the basic block) that the data belongs to
    :ivar int tid: thread id of the thread in which the routine or basic block run
    :ivar int pid: process id of the process in which the routine/basic block run
    :ivar int time_delta: the run-time of the routine/basic block in microseconds
    :ivar int entry_timestamp: the timestamp at which was the routine/basic block executed
    :ivar str workload: the parameters with which was the program containing the routine/basic block executed
    """
    def __init__(self, **kwargs):
        self.name = kwargs['name']
        self.tid = kwargs['tid']
        self.pid = kwargs['pid']
        self.time_delta = kwargs['time_delta']
        self.entry_timestamp = kwargs['entry_timestamp']
        self.workload = kwargs['workload']

    @abstractmethod
    def get_profile_data(self) -> dict:
        """ Creates the representation of the data suitable for perun profile.
        """
        pass


class FunctionCallRecord(Record):
    """ Class that represents the function/routine record

    :ivar int rtn_id: identification number of the routine
    :ivar int call_order: the order in which was the function called
    :ivar dict args: the arguments passed to the routine in a dictionary in format:
                     {"<param-index>":["<param-type>", int(<value>)], ...}
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.rtn_id = kwargs['rtn_id']
        self.call_order = kwargs['call_order']
        self.args = kwargs['args']

    def get_profile_data(self) -> dict:
        """ Creates suitable representation of the record data for the perun profile.
        :return dict: representation of data for perun profile
        """

        profile_data = {
            'workload': self.workload,
            'subtype': 'time delta',
            'type': 'mixed',
            'tid': self.tid,
            'uid': self.name,
            'call-order': self.call_order,
            'timestamp': self.entry_timestamp,
            'amount': self.time_delta
        }

        if self.args:
            for index in self.args:
                # Add arguments to the profile in following format:
                # <index>#<arg-type>: <arg-value>
                arg = self.args[index]
                #profile_data[f'arg{index}{arg[0]}'] = int(arg[1])
                # NOTE: ignoring the type of argument for now
                profile_data[f'arg{index}'] = arg[1]
        return profile_data

    def __repr__(self) -> str:
        # FIXME: order of output
        return 'RTN:\n' \
               f'args:           {self.args}\n'             \
               f'function_name:  {self.name}\n'             \
               f'delta:          {self.time_delta}\n'       \
               f'function_id:    {self.rtn_id}\n'           \
               f'tid:            {self.tid}\n'              \
               f'entry:          {self.entry_timestamp}\n'  \
               f'order:          {self.call_order}\n'


class BasicBlockRecord(Record):
    """ Class that represents the basic block record.

    :ivar int rtn_id: identification number for the routine that contains this basic block
    :ivar int bbl_id: identification number for the basic block
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.rtn_id = kwargs['rtn_id']
        self.bbl_id = kwargs['bbl_id']

    def get_profile_data(self) -> dict:
        """ Creates suitable representation of the record data for the perun profile.
        :return dict: representation of data for perun profile
        """
        return {
            'amount': self.time_delta,
            'timestamp': self.entry_timestamp,
            'uid': "BBL#" + self.name + "#" + str(self.bbl_id),
            'tid': self.tid,
            'type': 'mixed',
            'subtype': 'time delta',
            'workload': self.workload
        }

    def __repr__(self) -> str:
        return 'BBL:\n'                                      \
               f'function_name:  {self.name}\n'              \
               f'function_id:    {self.rtn_id}\n'            \
               f'block_id:       {self.bbl_id}\n'            \
               f'tid:            {self.tid}\n'               \
               f'delta:          {self.time_delta}\n'        \
               f'entry:          {self.entry_timestamp}\n'


def parse_data(file: str, workload: str, function_table=None):
    """ Parses the raw data output from pin and creates Records from it which are then converted to perun profile
    """

    # TODO: divide this function into more fundamental functions

    records = []  # TODO: remove
    not_paired_lines = []  # TODO: remove

    resources = []
    profile = Profile()

    with open(file, 'r') as raw_data:

        backlog_rtn = []
        backlog_bbl = []

        function_call_counter = 0
        line_counter = 0

        for line in raw_data:
            line_counter += 1

            # Parse a line of raw data
            line = line.strip('\n').split(';')
            # FIXME: Handle case where line[0] isn't either of the Granularity values
            current_format = RawDataEntry.BBL_FORMAT if int(line[0]) == Granularity.BBL else RawDataEntry.RTN_FORMAT
            data = {}

            # Store collected data in internal representation
            for key, value in zip(current_format, line):
                data[key] = int(value) if key != 'name' else value
            data = RawDataEntry(data)

            if function_table and len(line) > len(current_format): # There are additional function arguments
                # Function argument types collected by pyelftools are stored in function_table
                arg_types = function_table[data.name]
                arg_values = line[len(current_format):]  # Values of function arguments collected by PIN

                # Create new representation of raw data and store it
                arguments = {}
                for index, value in zip(arg_types, arg_values):

                    if arg_types[index] == 'char *':  # Store only length of a string
                        value = len(value)
                    if arg_types[index] == 'char':
                        value = ord(value)

                    arguments[index] = (arg_types[index], float(value))

                data.args = arguments

            # Decide which backlog to use based on the current data
            if data.is_function_granularity():
                function_call_counter += 1
                backlog = backlog_rtn
            else:
                backlog = backlog_bbl

            if not data.is_located_before():
                # Search backlog for its complementary (entry point) line
                if data in backlog:
                    data_entry_index = backlog.index(data)
                    data_entry = backlog[data_entry_index]

                    # Create new record from the pair of lines (entry point and the exit point)
                    if data.is_function_granularity():
                        record = FunctionCallRecord(name=data.name,
                                                    tid=data.tid, pid=data.pid,
                                                    time_delta=data.time_delta(data_entry),
                                                    entry_timestamp=data_entry.timestamp,
                                                    workload=workload,
                                                    rtn_id=data.rtn_id,
                                                    call_order=function_call_counter,
                                                    args=data_entry.args)
                    else:
                        record = BasicBlockRecord(name=data.name,
                                                  tid=data.tid, pid=data.pid,
                                                  time_delta=data.time_delta(data_entry),
                                                  entry_timestamp=data_entry.timestamp,
                                                  workload=workload,
                                                  rtn_id=data.rtn_id,
                                                  bbl_id=data.bbl_id)

                    backlog.pop(data_entry_index)
                    resources.append(record.get_profile_data())
                    records.append(record)
                else:  # TODO: remove
                    not_paired_lines.append(data)
            else:
                # Stash entry point line, so that it can be easily found when complementary line (exit point) is loaded
                # FIXME: Insert at the beginning could be better for searching if its overhead isn't worse
                backlog.append(data)

    #msg_to_stdout('------------ RECORDS ------------', 2)
    #for record in records:
        #if record.name == "QuickSortBad":
        #msg_to_stdout(record, 2)

    #not_paired_lines = not_paired_lines + backlog_rtn + backlog_bbl
    #msg_to_stdout('------------ NOT PAIRED ------------', 2)
    #for not_paired_line in not_paired_lines:
    #    msg_to_stdout(not_paired_line, 2)

    #msg_to_stdout(f'Number of pairs: {len(records)}', 2)
    #msg_to_stdout(f'Number of lines: {line_counter}', 2)
    #msg_to_stdout(f'In backlog:\n\trtn: {len(backlog_rtn)}\n\tbbl: {len(backlog_bbl)}', 2)

    profile.update_resources({'resources': resources}, 'global')
    #import pprint  # TODO: remove
    #pprint.pprint(resources)
    return profile

# TODO: Unify the function/routine naming
# TODO: Better debug messages in verbose mode
# TODO: figure out that the perun profile doesn't match expected format
