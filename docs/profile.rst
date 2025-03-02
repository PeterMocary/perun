.. _profile-format:

Perun's Profile Format
======================

.. _JSON: https://www.json.org/

Supported format is based on JSON_ with several restrictions regarding the keys (or regions) that
needs to be defined inside. The intuition of JSON_-like notation usage stems from its human
readability and well-established support in leading programming languages (namely Python and
JavaScript). Note, that however, the current version of format may generate huge profiles for some
collectors, since it can contain redundancies. We are currently exploring several techniques to
reduce the size of the profile.

.. image:: /../figs/lifetime-of-profile.*
   :width: 70%
   :align: center

The scheme above shows the basic lifetime of one profile. Performance profiles are generated by
units called collectors (or profilers). One can either generate the profiles by its own methods or
use one of the collectors from Perun's tool suite (see :ref:`collectors-list` for list of supported
collectors). Generated profile can then be postprocessed multiple times using postprocessing units
(see :ref:`postprocessors-list` for list of supported postprocessors), in order to e.g. normalize
the values. Once you are finished with the profiles, you can store it in the persistent storage
(see :ref:`internals-overview` for details how profiles are stored), where it will be compressed
and assigned to appropriate minor version origin, e.g. concrete commit. Both stored and freshly
generated profiles can be interpreted by various visualization techniques (see :ref:`views-list`
for list of visualization techniques).

.. _profile-spec:

Specification of Profile Format
-------------------------------

The generic scheme of the format can be simplified in the following regions.

.. code-block:: json

    {
        "origin": "",
        "header": {},
        "collector_info": {},
        "postprocessors": [],
        "snapshots": [],
        "chunks": {}
    }

`Chunks` region is currently in development, and is optional. `Snapshots` region contains the
actual collected resources  and can be changed through the further postprocessing phases, like e.g.
by :ref:`postprocessors-regression-analysis`. List of postprocessors specified in `postprocessors`
region can be updated by subsequent postprocessing analyses. Finally the `origin` region is only
present in non-assigned profiles. In the following we will decribe the regions in more details.

.. perfreg:: origin

.. code-block:: json

    {
        "origin": "f7f3dcea69b97f2b03c421a223a770917149cfae",
    }

Origin specifies the concrete minor version to which the profile corresponds. This key is present
only, when the profile is not yet assigned in the control system. Such profile is usually found in
`.perun/jobs` directory. Before storing the profile in persistent storage, `origin` is removed and
serves as validation that we are not assigning profiles to different minor versions. Assigning of
profiles corresponding to different minor versions would naturally screw with the project history.

The example region above specifies, that the profile corresponded to a minor version `f7f3dc` and
thus links the resources to the changes of this commit.

.. perfreg:: header

.. code-block:: json

    {
        "header": {
            "type": "time",
            "units": {
                "time": "s"
            },
            "cmd": "perun",
            "args": "status",
            "workload": "--short",
        }
    }

Header is a key-value dictionary containing basic specification of the profile, like e.g. rough
type of the performance profile, the actual command which was profiled, its parameters and input
workload (giving full project configuration). The following keys are included in this region:

The example above shows header of `time` profile, with resources measured in seconds. The profiled
command was ``perun status --short``, which was broken down to a command ``perun``, with parameter
``status`` and other parameter ``--short`` was considered to be workload (note that the definition
of workloads can vary and be used in different context).

.. perfkey:: type

Specifies rough type of the performance profile. Currently Perun consideres `time`, `mixed` and
`memory`. We further plan to expand the list of choices to include e.g. `network`, `filesystem` or
`utilization` profile types.

.. perfkey:: units

Map of types (and possible subtypes) of resources to their used metric units. Note that collector
should guarantee that resources are unified in units. E.g. `time` can be measured in `s` or `ms`,
`memory` of subtype `malloc` can be measured in `B` or `kB`, read/write thoroughput can be measured
in `kB/s`, etc.

.. perfkey:: cmd

Specifies the command which was profiled and yielded the generated the profile. This can be either
some script (e.g. ``perun``), some command (e.g. ``ls``), or execution of binary (e.g. ``./out``.
In general this corresponds to a profiled application. Note, that some collectors are working with
their own binaries and thus do not require the command to be specified at all (like e.g.
:ref:`collectors-trace` and will thus omit the actual usage of the command), however, this key
can still be used e.g. for tagging the profiles.

.. perfkey:: args

Specifies list of arguments (or parameters) for command :pkey:`cmd`. This is used for more fine
distinguishing of profiles regarding its parameters (e.g. when we run command with different
optimizations, etc.). E.g. if take ``ls`` command as an example, ``-al`` can be considered as
parameter. This key is optional, can be empty string.

.. perfkey:: workload

Similarly to parameters, workloads refer to a different inputs that are supplied to profiled
command with given arguments. E.g. when one profiles text processing application, workload will
refer to a concrete text files that are used to profile the application. In case of the ``ls -al``
command with parameters, ``/`` or ``./subdir`` can be considered as workloads. This key is
optional, can be empty string.

.. perfreg:: collector_info

.. code-block:: json

    {
        "collector_info": {
            "name": "complexity",
            "params": {
                "sampling": [
                    {
                        "func": "SLList_insert",
                        "sample": 1
                    },
                ],
                "internal_direct_output": false,
                "internal_storage_size": 20000,
                "files": [
                    "../example_sources/simple_sll_cpp/main.cpp",
                    "../example_sources/simple_sll_cpp/SLList.h",
                    "../example_sources/simple_sll_cpp/SLListcls.h"
                ],
                "target_dir": "./target",
                "rules": [
                    "SLList_init",
                    "SLList_insert",
                    "SLList_search",
                ]
            },
        }
    }

Collector info contains configuration of the collector, which was used to capture resources and
generate the profile.

.. perfkey:: collector_info.name

Name of the collector (or profiler), which was used to generate the profile. This is used e.g. in
displaying the list of the registered and unregistered profiles in ``perun status``, in order to
differentiate between profiles collected by different profilers.

.. perfkey:: collector_info.params

The configuration of the collector in the form of `(key, value)` dictionary.

The example above lists the configuration of :ref:`collectors-trace` (for full specification
of parameters refer to :ref:`collectors-trace-cli`). This configurations e.g. specifies, that
the list of `files` will be compiled into the `target_dir` with custom Makefile and these sources
will be used create a new binary for the project (prepared for profiling), which will profile
function specified by `rules` w.r.t specified `sampling`.

.. perfreg:: postprocessors

.. code-block:: json

    {
        "postprocessors": [
            {
                "name": "regression_analysis",
                "params": {
                    "method": "full",
                    "models": [
                        "constant",
                        "linear",
                        "quadratic"
                    ]
                },
            }
        ],
    }

List of configurations of postprocessing units in order they were applied to the profile (with keys
analogous to :preg:`collector_info`).

The example above specifies list with one postprocessor, namely the
:ref:`postprocessors-regression-analysis` (for full specification refer to
:ref:`postprocessors-regression-analysis-cli`). This configuration applied regression analysis and
using full `method` fully computed models for constant, linear and quadratic `models`.

.. perfreg:: snapshots

.. code-block:: json

    {
        "snapshots": [
            {
                "time": "0.025000",
                "resources": [
                    {
                        "type": "memory",
                        "subtype": "malloc",
                        "address": 19284560,
                        "amount": 4,
                        "trace": [
                            {
                                "source": "../memory_collect_test.c",
                                "function": "main",
                                "line": 22
                            },
                        ],
                        "uid": {
                            "source": "../memory_collect_test.c",
                            "function": "main",
                            "line": 22
                        }
                    },
                ],
                "models": []
            }, {
                "time": "0.050000",
                "resources": [
                    {
                        "type": "memory",
                        "subtype": "free",
                        "address": 19284560,
                        "amount": 0,
                        "trace": [
                            {
                                "source": "../memory_collect_test.c",
                                "function": "main",
                                "line": 22
                            },
                        ],
                        "uid": {
                            "source": "../memory_collect_test.c",
                            "function": "main",
                            "line": 22
                        }
                    },
                ],
                "models": []
            },
        ]
    }

`Snapshots` contains the list of actual resources that were collected by the specified collector
(:pkey:`collector_info.name`). Each snapshot is represented by its `time`, list of captured
`resources` and optionally list of `models` (refer to :ref:`postprocessors-regression-analysis` for
more details). The actual specification of resources varies w.r.t to used collectors.

.. perfkey:: time

`Time` specifies the timestamp of the given snapshot. The example above contains two snapshots,
first captured after 0.025s and other after 0.05s of running time.

.. perfkey:: resources

`Resources` contains list of captured profiling data. Their actual format varies, and is rather
flexible. In order to model the actual amount of resources, we advise to use `amount` key to
quantify the size of given metric and use `type` (and possible `subtype`) in order to link
resources to appropriate metric units.

The resources above were collected by :ref:`collectors-memory`, where `amount` specifies the number
of bytes allocated of given memory `subtype` at given `address` by specified `trace` of functions.
The first snapshot contains one resources corresponding ot `4B` of memory allocated by `malloc` in
function `main` on line `22` in `memory_collect_test.c` file. The other snapshots contains record
of deallocation of the given resource by `free`.

.. code-block:: json

    {
        "amount": 0.59,
        "type": "time",
        "uid": "sys"
    }

These resources were collected by :ref:`collectors-time`, where `amount` specifies the sys time of
the profile application (as obtained by ``time`` utility).

.. code-block:: json

    {
        "amount": 11,
        "subtype": "time delta",
        "type": "mixed",
        "uid": "SLList_init(SLList*)",
        "structure-unit-size": 0
    }

These resources were collected by :ref:`collectors-trace`. `Amount` here represents the
difference between calling and returning the function `uid` in miliseconds, on structure of size
given by `structure-unit-size`. Note that these resources are suitable for
:ref:`postprocessors-regression-analysis`.

.. perfkey:: models

.. code-block:: json

    {
        "uid": "SLList_insert(SLList*, int)",
        "r_square": 0.0017560012128507133,
        "coeffs": [
            {
                "value": 0.505375215875552,
                "name": "b0"
            },
            {
                "value": 9.935159839322705e-06,
                "name": "b1"
            }
        ],
        "x_start": 0,
        "x_end": 11892,
        "model": "linear",
        "method": "full",
    }

`Models` is a list of models obtained by :ref:`postprocessors-regression-analysis`. Note that the
ordering of models in the list has no meaning at all. The model above corresponds to behaviour of
the function ``SLList_insert``, and corresponds to a linear function of :math:`amount = b_0 + b_1 *
size` (where size corresponds to the `structure-unit-size` key of the resource) on interval
:math:`(0, 11892)`. Hence, we can estimate the complexity of function ``SLList_insert`` to be
linear.

.. perfreg:: chunks

This region is currently in proposal. `Chunks` are meant to be a look-up table which maps unique
identifiers to a larger portions of JSON_ regions. Since lots of informations are repeated through
the profile (e.g. the `traces` in :ref:`collectors-memory`), replacing such regions with reference
to the look-up table should greatly reduce the size of profiles.

.. _profile-api:

Profile API
-----------

.. automodule:: perun.profile.helpers

.. automodule:: perun.profile.factory

.. autoclass:: Profile
   :members: all_resources, all_snapshots, all_models, all_filtered_models

.. _profile-conversion-api:

Profile Conversions API
-----------------------

.. automodule:: perun.profile.convert

.. autofunction:: resources_to_pandas_dataframe

.. autofunction:: to_flame_graph_format

.. autofunction:: plot_data_from_coefficients_of

.. _profile-query-api:

Profile Query API
-----------------

.. automodule:: perun.profile.query

.. autofunction:: all_items_of

.. autofunction:: all_numerical_resource_fields_of

.. autofunction:: unique_resource_values_of

.. autofunction:: all_key_values_of

.. autofunction:: unique_model_values_of
