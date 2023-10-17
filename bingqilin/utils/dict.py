from enum import Enum
from typing import Any, Dict, Mapping, MutableMapping, MutableSequence

DEFAULT_PATH_DELIMITER = "/"


class SEQUENCE_MERGE_STRATEGY(Enum):
    """
    Behavior to use when merging two sequences.

    REPLACE: Replace the current value with the newer one
    APPEND: Append the newer value to the current one
    UNIQUE: Append all elements from the newer one to the current value
            if they don't exist in the current sequence

    NOTE: If the elements in either sequence are not hashable, a TypeError will be raised.
    """

    REPLACE = "replace"
    CONCATENATE = "concatenate"
    UNIQUE = "unique"


def iter_dict_key_paths(in_dict, prefix="", path_delimiter=DEFAULT_PATH_DELIMITER):
    for key, value in in_dict.items():
        if prefix:
            curr_path = path_delimiter.join([prefix, key])
        else:
            curr_path = key
        if isinstance(value, Mapping):
            yield from iter_dict_key_paths(in_dict[key], curr_path, path_delimiter)
        else:
            yield curr_path, value


def set_key_path(
    in_dict,
    key_path,
    new_value,
    create_parents=True,
    path_delimiter=DEFAULT_PATH_DELIMITER,
    merge_strategy=SEQUENCE_MERGE_STRATEGY.REPLACE,
):
    parts = key_path.split(path_delimiter)
    if len(parts) == 1:
        in_dict[key_path] = new_value
        return

    dict_child = in_dict
    for part in parts[:-1]:
        if (part not in dict_child or not dict_child[part]) and create_parents:
            dict_child[part] = {}
        dict_child = dict_child[part]

    if not isinstance(dict_child, MutableMapping):
        raise TypeError(
            "Only mappings values can be set. "
            f'Value at path "{path_delimiter.join(parts[:-1])}" '
            f"is of type {type(dict_child)}."
        )

    if parts[-1] not in dict_child or not isinstance(
        dict_child[parts[-1]], MutableSequence
    ):
        dict_child[parts[-1]] = new_value
    else:
        if merge_strategy == SEQUENCE_MERGE_STRATEGY.REPLACE:
            dict_child[parts[-1]] = new_value
        elif merge_strategy == SEQUENCE_MERGE_STRATEGY.CONCATENATE:
            dict_child[parts[-1]] += new_value
        elif merge_strategy == SEQUENCE_MERGE_STRATEGY.UNIQUE:
            sequence_type = type(dict_child[parts[-1]])
            dict_child[parts[-1]] = sequence_type(
                set(dict_child[parts[-1]] + new_value)
            )


def merge(
    base: Dict[str, Any],
    *dicts: Dict[str, Any],
    path_delimiter: str = DEFAULT_PATH_DELIMITER,
    create_parent_dicts: bool = True,
    sequence_merge_strategy: SEQUENCE_MERGE_STRATEGY = SEQUENCE_MERGE_STRATEGY.REPLACE,
) -> dict:
    """This merge() does a deeper reconciliation of nested objects than what `dict.update()` would do.
    Consider two dicts:

    a = {'a': {'d': {'e': 'xyz'}}, 'b': True, 'c': 123}
    b = {'a': {'d': {'f': 'uvw'}, 'g': 101}}

    This function will attempt to merge as many keys in nested objects as it can, and only
    replacing if the value is a basic type (except for sequences). The expected output would be:

    {'a': {'d': {'e': 'xyz', 'f': 'uvw'}}, 'b': True, 'c': 123, 'g': 101}

    Args:
        base (dict): A base dict to merge values into
        path_delimiter (str, optional): A delimiter to describe the keys to access a value in a nested dict.
            Defaults to "/". Can be changed in case there are keys that contain a "/".
        create_parent_dicts (bool, optional): If the key doesn't exist in the base dict and is supposed to contain
            a nested dict, create one. Disable this option if you want to enforce that the merging dict is
            a strict subset. Defaults to True.
        sequence_merge_strategy (str, optional): Behavior to use when merging two sequences.
            See the `SEQUENCE_MERGE_STRATEGY` class. Defaults to "replace".

    Returns:
        dict: The merged dict
    """
    if not dicts:
        return base

    for current_dict in [d for d in dicts if d]:
        for key_path, value in iter_dict_key_paths(
            current_dict, path_delimiter=path_delimiter
        ):
            set_key_path(
                base,
                key_path,
                value,
                create_parents=create_parent_dicts,
                path_delimiter=path_delimiter,
                merge_strategy=sequence_merge_strategy,
            )

    return base
