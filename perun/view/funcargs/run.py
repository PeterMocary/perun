""" Scatter plot of dependence of function run--time on values of its arguments
"""

import click
import re

from perun.profile.factory import pass_profile
from perun.profile.factory import Profile
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt


def _get_resource_collectables_merged_template(resource):
    """ Creates a template for resource that are collectable for further use

    :param  dict resource: the resource for which to create template

    :returns dict merged_resource_template: dictionary template from resource's collectables
    """
    merged_resource_template = {}
    for key in resource:
        if key in Profile.collectable or re.match(r'^arg[0-9]+.*', key):
            merged_resource_template[key] = [resource[key]]

    return merged_resource_template


def _merge_collectable_resources(dest: dict, src: dict):
    """ Combines resources that are collectable - have different values for a key in different executions

    :param dict dest: appends the resources to this dict
    :param dict src: takes resources from this dict
    """

    for key in src:
        if key in Profile.collectable or re.match(r'^arg[0-9]+.*', key):
            dest[key].append(src[key])


def get_function_dataframes(profile):
    """ Converts a profile to a dictionary containing all the information about functions.

    :param Profile profile: Profile from which to gather the information about functions

    :returns dict unique_resources: dictionary of functions with their collected data
    """

    unique_resources = {}

    # merge the collectable data from profile resources
    for resource in profile.all_resources(True):
        resource = resource[1]  # Ignores snapshots

        if resource['uid'] not in unique_resources:
            if not re.match(r'^BBL#.*#[0-9]+#[0-9]+$', resource['uid']):  # filter out basic blocks
                unique_resources[resource['uid']] = _get_resource_collectables_merged_template(resource)
        else:
            _merge_collectable_resources(unique_resources[resource['uid']], resource)

    # convert the data to pandas DataFrames
    for resource_uid in unique_resources:
        unique_resources[resource_uid] = pd.DataFrame(data=unique_resources[resource_uid])

    return unique_resources


def _get_column_keys_for_args(function_data: pd.DataFrame):
    """ Retrieves argument keys from selected dataframe

    :param DataFrame function_data: Dataframe from which to retrieve argument keys

    :returns list args: list of argument keys from the selected dataframe
    """
    args = []
    for column_name in function_data.columns:
        if re.match(r'^arg[0-9]+.*', column_name):
            args.append(column_name)

    return args


@click.command()
@click.option('--squash', '-s', is_flag=True, default=False,
              help="Squashes all arguments to a single graph.")
@click.option('--function_name', '-fn', type=str, default=None,
              help="Select a function (by its name) which arguments to plot.")
@pass_profile
def funcargs(profile, squash, function_name):
    sns.set(font_scale=1.0)
    function_data = get_function_dataframes(profile)
    function_data_with_args = {}
    if function_name and function_name not in function_data.keys():
        raise Exception("Wrong function name!")

    # filter functions with arguments only
    max_cols = -1
    for func_name, func_dataframe in function_data.items():
        if function_name and func_name != function_name:
            continue  # filter for the selected function data only
        column_keys = _get_column_keys_for_args(func_dataframe)
        column_keys_cnt = len(column_keys)
        if column_keys_cnt > 0:  # function with arguments
            if func_dataframe.size >= 10:  # function was called at least 10 times
                max_cols = column_keys_cnt if max_cols < column_keys_cnt else max_cols
                function_data_with_args[func_name] = func_dataframe

    for function_name, function_dataframe in function_data_with_args.items():
        column_keys = _get_column_keys_for_args(function_dataframe)

        # SHOWCASES THE STATE WITHOUT ARGS AVAILABLE
        # fig_without_args = plt.figure()
        # ax = fig_without_args.add_subplot()
        # x_vec = function_dataframe.index + 1
        # without_args = sns.scatterplot(ax=ax, data=function_dataframe, x=x_vec, y='amount')
        # without_args.set(ylabel='Function run-time [μs]', xlabel='Execution')
        # fig_without_args.suptitle(function_name)

        subplots_cnt = 1 if squash else len(column_keys)
        fig, axes = plt.subplots(1, subplots_cnt, sharey=True)
        fig.suptitle(function_name)

        if squash:
            for col_name in column_keys:
                a = sns.scatterplot(data=function_dataframe, x=col_name, y='amount')
            a.set(ylabel='Function run-time [μs]', xlabel='Argument value')
            labels = []
            for col_name in column_keys:
                arg_type_and_name = col_name.split('#')[1:]
                xlabel = " ".join(arg_type_and_name)
                if arg_type_and_name[0] == 'char *':
                    xlabel = xlabel + "(length)"
                labels.append(xlabel)

            plt.legend(labels=labels, title='Arguments legend')

        elif len(column_keys) == 1:
            a = sns.scatterplot(data=function_dataframe, x=column_keys[0], y='amount')
            arg_type_and_name = column_keys[0].split('#')[1:]
            xlabel = 'Argument value'
            if arg_type_and_name[0] == 'char *':
                xlabel = 'String length'
            a.set(ylabel='Function run-time [μs]', xlabel=xlabel, title=' '.join(arg_type_and_name))

        else:
            for col, col_name in enumerate(column_keys):
                arg_type_and_name = col_name.split('#')[1:]
                xlabel = 'Argument value'
                if arg_type_and_name[0] == 'char *':
                    xlabel = 'String length'
                a = sns.scatterplot(ax=axes[col], data=function_dataframe, x=col_name, y="amount")
                a.set(ylabel="Function run-time [μs]", xlabel=xlabel, title=" ".join(arg_type_and_name))

    plt.show()
