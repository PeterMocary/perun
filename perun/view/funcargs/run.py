import click
import re

from perun.profile.factory import pass_profile
from perun.profile.factory import Profile
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt


def _get_resource_collectables_merged_template(resource):

    merged_resource_template = {}
    for key in resource:
        if key in Profile.collectable or re.match(r'^arg[0-9]+.*', key):
            merged_resource_template[key] = [resource[key]]

    return merged_resource_template


def _merge_collectable_resources(dest: dict, src: dict):

    for key in src:
        if key in Profile.collectable or re.match(r'^arg[0-9]+.*', key):
            dest[key].append(src[key])


def get_function_dataframes(profile):

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

        subplots_cnt = 1 if squash else len(column_keys)
        fig, axes = plt.subplots(1, subplots_cnt, sharey=True)
        fig.suptitle(function_name)

        if squash:
            for col_name in column_keys:
                a = sns.scatterplot(data=function_dataframe, x=col_name, y='amount')
            a.set(ylabel='function run-time [μs]', xlabel='argument value')
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
            xlabel = 'argument value'
            if arg_type_and_name[0] == 'char *':
                xlabel = 'string length'
            a.set(ylabel='function run-time [μs]', xlabel=xlabel, title=' '.join(arg_type_and_name))
        else:
            for col, col_name in enumerate(column_keys):
                arg_type_and_name = col_name.split('#')[1:]
                xlabel = 'argument value'
                if arg_type_and_name[0] == 'char *':
                    xlabel = 'string length'
                a = sns.scatterplot(ax=axes[col], data=function_dataframe, x=col_name, y="amount")
                a.set(ylabel="function run-time [μs]", xlabel=xlabel, title=" ".join(arg_type_and_name))

    plt.show()
