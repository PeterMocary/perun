"""Module with available regression computational methods.

This module exposes all currently implemented computational methods for regression analysis.

"""

from __future__ import annotations

# Standard Imports
from typing import Any, Optional, Iterator, Protocol
import collections

# Third-Party Imports

# Perun Imports
from perun.postprocess.regression_analysis import regression_models, tools
from perun.utils import exceptions
from perun.utils import log


class ComputationMethod(Protocol):
    def __call__(self, *args: Any, **kwargs: Any) -> Iterator[dict[str, Any]]:
        """Empty method"""


def get_supported_param_methods() -> list[str]:
    """Provides all currently supported computational methods as a list of their names.

    :return: the names of all supported methods
    """
    return list(_METHODS.keys())


def compute(
    data_gen: Iterator[tuple[list[float], list[float], str]],
    method: str,
    models: tuple[str],
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """The regression analysis wrapper for various computation methods.

    :param data_gen: the generator object with collected data (data provider generators)
    :param method: the _METHODS key value indicating requested computation method
    :param models: tuple of requested regression models to compute
    :param kwargs: various additional configuration arguments for specific models
    :raises GenericRegressionExceptionBase: derived versions which are used in the computation
        functions
    :raises DictionaryKeysValidationFailed: in case the data format dictionary is incorrect
    :raises TypeError: if the required function arguments are not in the unpacked dictionary input
    :return: the computation results
    """
    # Split the models into derived and standard ones
    derived, models = regression_models.filter_derived(models)
    analysis = []
    for chunk in data_gen:
        try:
            # First compute all the standard models
            for result in _METHODS[method](chunk[0], chunk[1], models, **kwargs):
                result["uid"] = chunk[2]
                result["method"] = method
                analysis.append(result)
        except exceptions.GenericRegressionExceptionBase as exc:
            log.minor_info(
                f"unable to perform regression analysis on function '{chunk[2]} due to: {exc}",
            )
    # Compute the derived models
    for der in compute_derived(derived, analysis, **kwargs):
        analysis.append(der)
    # Create output dictionaries
    return list(map(_transform_to_output_data, analysis))


def compute_derived(
    derived_models: tuple[str], analysis: list[dict[str, Any]], **kwargs: Any
) -> Iterator[dict[str, Any]]:
    """The computation wrapper for derived models.

    :param derived_models: collection of derived models to compute
    :param analysis: the already computed standard regression models
    :param kwargs: additional optional parameters
    :return: generator object which produces results one by one
    """
    if derived_models:
        for der in regression_models.map_keys_to_models(derived_models):
            for result in der["derived"](analysis, der, **kwargs):
                yield result


def full_computation(
    x_pts: list[float], y_pts: list[float], computation_models: tuple[str], **_: Any
) -> Iterator[dict[str, Any]]:
    """The full computation method which fully computes every specified regression model.

    The method might have performance issues in case of too many models or data points.

    :param x_pts: the list of x points coordinates
    :param y_pts: the list of y points coordinates
    :param computation_models: the collection of regression models to compute
    :raises GenericRegressionExceptionBase: derived versions which are used in the computation
        functions
    :raises DictionaryKeysValidationFailed: in case the data format dictionary is incorrect
    :raises TypeError: if the required function arguments are not in the unpacked dictionary input
    :return: the generator object which produces computed models one by one as a
        transformed output data dictionary
    """
    # Get all the models properties
    for model in regression_models.map_keys_to_models(computation_models):
        # Update the properties accordingly
        model["steps"] = 1
        model = _build_uniform_regression_data_format(x_pts, y_pts, model)
        # Compute each model
        for result in model["computation"](**model):
            yield result


def iterative_computation(
    x_pts: list[float],
    y_pts: list[float],
    computation_models: tuple[str],
    steps: int,
    **_: Any,
) -> Iterator[dict[str, Any]]:
    """The iterative computation method.

    This method splits the regression data evenly into random parts, which are incrementally
    computed. Only the currently best fitting model is computed in each step.

    This method might produce only local result (local extrema), but it's generally faster than
    the full computation method.

    :param x_pts: the list of x points coordinates
    :param y_pts: the list of y points coordinates
    :param computation_models: the collection of regression models to compute
    :param steps: number of steps to slit the computation into
    :raises GenericRegressionExceptionBase: derived versions which are used in the computation
        functions
    :raises DictionaryKeysValidationFailed: in case the data format dictionary is incorrect
    :raises TypeError: if the required function arguments are not in the unpacked dictionary input
    :return: the generator object which produces best fitting model as a transformed data
        dictionary
    """
    x_pts, y_pts = tools.shuffle_points(x_pts, y_pts)

    # Do the initial step for specified models
    model_generators, results = _models_initial_step(x_pts, y_pts, computation_models, steps)
    best_fit = -1
    while True:
        try:
            # Get the best fitting model and do next computation step
            best_fit = _find_best_fitting_model(results)
            results[best_fit] = next(model_generators[best_fit])
        except StopIteration:
            # The best fitting model finished the computation, end of computation
            yield results[best_fit]
            break


def interval_computation(
    x_pts: list[float],
    y_pts: list[float],
    computation_models: tuple[str],
    steps: int,
    **_: Any,
) -> Iterator[dict[str, Any]]:
    """The interval computation method.

    This method splits the regression data into evenly distributed sorted parts (i.e. intervals)
    and each interval is computed separately using the full computation.

    This technique allows to find different regression models in each interval and thus discover
    different trace behaviour for algorithm based on it's input size.

    :param x_pts: the list of x points coordinates
    :param y_pts: the list of y points coordinates
    :param computation_models: the collection of regression models to compute
    :param steps: number of steps to slit the computation into
    :raises GenericRegressionExceptionBase: derived versions which are used in the computation
        functions
    :raises DictionaryKeysValidationFailed: in case the data format dictionary is incorrect
    :raises TypeError: if the required function arguments are not in the unpacked dictionary input
    :return: the generator object which produces computed models one by one for every interval as a
        transformed output data dictionary
    """
    # Sort the regression data
    x_pts, y_pts = tools.sort_points(x_pts, y_pts)
    # Split the data into intervals and do a full computation on each one of them
    for part_start, part_end in tools.split_sequence(len(x_pts), steps):
        interval_gen = full_computation(
            x_pts[part_start:part_end], y_pts[part_start:part_end], computation_models
        )
        # Provide result for each model on every interval
        results = []
        for model in interval_gen:
            results.append(model)

        # Find the best model for the given interval
        best_fit = _find_best_fitting_model(results)
        yield results[best_fit]


def initial_guess_computation(
    x_pts: list[float],
    y_pts: list[float],
    computation_models: tuple[str],
    steps: int,
    **_: Any,
) -> Iterator[dict[str, Any]]:
    """The initial guess computation method.

    This method does initial computation of a data sample and then computes the rest of the model
    that has best r^2 coefficient.

    This method might produce only local result (local extrema), but it's generally faster than the
    full computation method.

    :param x_pts: the list of x points coordinates
    :param y_pts: the list of y points coordinates
    :param computation_models: the collection of regression models to compute
    :param steps: number of steps to slit the computation into
    :raises GenericRegressionExceptionBase: derived versions which are used in the computation
        functions
    :raises DictionaryKeysValidationFailed: in case the data format dictionary is incorrect
    :raises TypeError: if the required function arguments are not in the unpacked dictionary input
    :return: the generator object that produces the complete result in one step
    """
    x_pts, y_pts = tools.shuffle_points(x_pts, y_pts)

    # Do the initial step for specified models
    model_generators, results = _models_initial_step(x_pts, y_pts, computation_models, steps)
    # Find the model that fits the most
    best_fit = _find_best_fitting_model(results)

    # Now compute the rest of the model
    while True:
        try:
            results[best_fit] = next(model_generators[best_fit])
        except StopIteration:
            # The best fitting model finished the computation, end of computation
            yield results[best_fit]
            break


def bisection_computation(
    x_pts: list[float], y_pts: list[float], computation_models: tuple[str], **_: Any
) -> Iterator[dict[str, Any]]:
    """The bisection computation method.

    This method computes the best fitting model for the whole profiling data and then perform
    interval bisection in order to find potential difference between interval models.

    :param x_pts: the list of x points coordinates
    :param y_pts: the list of y points coordinates
    :param computation_models: the collection of regression models to compute
    :raises GenericRegressionExceptionBase: derived versions which are used in the computation
        functions
    :raises DictionaryKeysValidationFailed: in case the data format dictionary is incorrect
    :raises TypeError: if the required function arguments are not in the unpacked dictionary input
    :return: the generator object that produces interval models in order
    """
    # Sort the regression data
    x_pts, y_pts = tools.sort_points(x_pts, y_pts)

    # Compute the initial model on the whole data set
    init_model = _compute_bisection_model(x_pts, y_pts, computation_models)

    # Do bisection and try to find different model for the new sections
    for sub_model in _bisection_step(x_pts, y_pts, computation_models, init_model):
        yield sub_model


def _compute_bisection_model(
    x_pts: list[float],
    y_pts: list[float],
    computation_models: tuple[str],
    **kwargs: Any,
) -> dict[str, Any]:
    """Compute specified models on a given data set and find the best fitting model.

    Currently, uses the full computation method.

    :param x_pts: the list of x points coordinates
    :param y_pts: the list of y points coordinates
    :param computation_models: the collection of regression models that will be
        computed
    :param kwargs: additional configuration parameters
    :raises GenericRegressionExceptionBase: derived versions which are used in the computation
        functions
    :raises DictionaryKeysValidationFailed: in case the data format dictionary is incorrect
    :raises TypeError: if the required function arguments are not in the unpacked dictionary input
    :return: the best fitting model
    """

    results = []
    # Compute the step using the full computation
    for result in full_computation(x_pts, y_pts, computation_models, **kwargs):
        results.append(result)
    # Find the best model
    return results[_find_best_fitting_model(results)]


def _bisection_step(
    x_pts: list[float],
    y_pts: list[float],
    computation_models: tuple[str],
    last_model: dict[str, Any],
) -> Iterator[dict[str, Any]]:
    """The bisection step computation.

    Performs one computation step for bisection. Splits the interval set by x_pts, y_pts and
    tries to compute each half. In case of model change, the interval is split again and the
    process repeats. Otherwise, the last model is used as a final model.

    :param x_pts: the list of x points coordinates
    :param y_pts: the list of y points coordinates
    :param computation_models: the collection of regression models to compute
    :param last_model: the full interval model that is split
    :raises GenericRegressionExceptionBase: derived versions which are used in the computation
        functions
    :raises DictionaryKeysValidationFailed: in case the data format dictionary is incorrect
    :raises TypeError: if the required function arguments are not in the unpacked dictionary input
    :return: the generator object that produces interval result
    """
    # Split the interval and compute each one of them
    half_models = []
    parts = []
    for part_start, part_end in tools.split_sequence(len(x_pts), 2):
        half_models.append(
            _compute_bisection_model(
                x_pts[part_start:part_end],
                y_pts[part_start:part_end],
                computation_models,
            )
        )
        parts.append((part_start, part_end))

    # The half models are not different, return the full interval model
    if (
        half_models[0]["model"] == last_model["model"]
        and half_models[1]["model"] == last_model["model"]
    ):
        yield last_model
        return

    def _model_bisection(i: int) -> Iterator[dict[str, Any]]:
        """Wrapper that iterates over half of the model

        :param i: either 0 or 1 for iteration of left or right model
        """
        x, y = parts[i][0], parts[i][1]
        for half_model in _bisection_solve_half_model(
            x_pts[x:y], y_pts[x:y], computation_models, half_models[i], last_model
        ):
            yield half_model

    # Check the first half interval and continue with bisection if needed
    yield from _model_bisection(0)
    # Check the second half interval and continue with bisection if needed
    yield from _model_bisection(1)


def _bisection_solve_half_model(
    x_pts: list[float],
    y_pts: list[float],
    computation_models: tuple[str],
    half_model: dict[str, Any],
    last_model: dict[str, Any],
) -> Iterator[dict[str, Any]]:
    """Helper function for solving half intervals and producing their results.

    The functions check if the model has changed for the given half and if yes, then continues
    with bisection - otherwise the half model is used as the final one for the interval.

    :param x_pts: the list of x points coordinates
    :param y_pts: the list of y points coordinates
    :param computation_models: the collection of regression models to compute
    :param half_model: the half interval model
    :param last_model: the full interval model that is split
    """
    if half_model["model"] != last_model["model"]:
        # The model is different, continue with bisection
        try:
            for submodel in _bisection_step(x_pts, y_pts, computation_models, half_model):
                yield submodel
        # Too few submodel points to perform regression, use the half model instead
        except exceptions.InvalidPointsException:
            yield half_model
    else:
        # The model is the same
        yield half_model


def _models_initial_step(
    x_pts: list[float], y_pts: list[float], computation_models: tuple[str], steps: int
) -> tuple[list[Iterator[dict[str, Any]]], list[dict[str, Any]]]:
    """Performs initial step with specified models in multistep methods.

    :param x_pts: the list of x points coordinates
    :param y_pts: the list of y points coordinates
    :param computation_models: the collection of regression models to compute
    :param steps: number of total steps
    :raises GenericRegressionExceptionBase: derived versions which are used in the computation
        functions
    :raises DictionaryKeysValidationFailed: in case the data format dictionary is incorrect
    :raises TypeError: if the required function arguments are not in the unpacked dictionary input
    :return: list of model generators, list of model initial step results
    """
    model_generators = []
    results = []
    # Get all the models properties
    for model in regression_models.map_keys_to_models(computation_models):
        # Transform the properties
        model["steps"] = steps
        data = _build_uniform_regression_data_format(x_pts, y_pts, model)
        # Do a single computational step for each model
        model_generators.append(model["computation"](**data))
        results.append(next(model_generators[-1]))
    return model_generators, results


def _find_best_fitting_model(model_results: list[dict[str, Any]]) -> int:
    """Finds the model which is currently the best fitting one.

    This function operates on a (intermediate) result dictionaries,
    where 'r_square' key is required.

    :param model_results: the list of result dictionaries for models
    :return: the index of best fitting model amongst the list
    """
    # Guess the best fitting model is the first one
    best_fit = 0
    for i in range(1, len(model_results)):
        # Compare and find the best one
        if model_results[i]["r_square"] > model_results[best_fit]["r_square"]:
            best_fit = i
    return best_fit


def _transform_to_output_data(
    data: dict[str, Any], extra_keys: Optional[list[str]] = None
) -> dict[str, Any]:
    """Transforms the data dictionary into their output format - omitting computational details
    and keys that are not important for the result and its further manipulation.

    The function provides dictionary with 'model', 'coeffs', 'r_square', 'x_start' and
    'x_end' keys taken from the data dictionary. The function also allows to specify
    extra keys to be included in the output dictionary. If certain key is missing in the data
    dictionary, then it's not included in the output dictionary. Coefficients are saved with
    default names 'b0', 'b1'...

    :param data: the data dictionary with results
    :param extra_keys: the extra keys to include
    :raises DictionaryKeysValidationFailed: in case the data format dictionary is incorrect
    :return: the output dictionary
    """
    tools.validate_dictionary_keys(data, ["model", "coeffs", "r_square", "x_start", "x_end"], [])

    # Specify the keys which should be directly mapped
    transform_keys = ["model", "r_square", "x_start", "x_end", "method", "uid"]
    transform_keys += extra_keys or []
    transformed = {key: data[key] for key in transform_keys if key in data}
    # Transform the coefficients
    transformed["coeffs"] = []
    for idx, coeff in enumerate(data["coeffs"]):
        transformed["coeffs"].append({"name": f"b{idx}", "value": coeff})

    return transformed


def _build_uniform_regression_data_format(
    x_pts: list[float], y_pts: list[float], model: dict[str, Any]
) -> dict[str, Any]:
    """Creates the uniform regression data dictionary from the model properties and regression
    data points.

    The uniform data dictionary is used in the regression computation as it allows to build
    generic and easily extensible computational methods and models.

    :param x_pts: the list of x points coordinates
    :param y_pts: the list of y points coordinates
    :param model: the regression model properties
    :raises InvalidPointsException: if the points count is too low or their coordinates list have
        different lengths
    :raises DictionaryKeysValidationFailed: in case the data format dictionary is incorrect
    :return: the uniform data dictionary
    """
    # Check the requirements
    tools.check_points(len(x_pts), len(y_pts), tools.MIN_POINTS_COUNT)
    tools.validate_dictionary_keys(model, ["data_gen"], ["x", "y"])

    model["x_pts"] = x_pts
    model["y_pts"] = y_pts
    # Initialize the data generator
    model["data_gen"] = model["data_gen"](**model)
    return model


# supported methods mapping
# - every method must be called with proper argument signature in 'compute' function
# -- the signature: x, y, models, **kwargs
_METHODS: collections.OrderedDict[str, ComputationMethod] = collections.OrderedDict(
    [
        ("full", full_computation),
        ("iterative", iterative_computation),
        ("interval", interval_computation),
        ("initial_guess", initial_guess_computation),
        ("bisection", bisection_computation),
    ]
)
