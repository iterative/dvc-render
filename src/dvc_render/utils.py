from collections.abc import MutableMapping


def list_dict_to_dict_list(list_dict):
    """Convert from list of dictionaries to dictionary of lists."""
    if not list_dict:
        return {}
    flat_list_dict = [flatten(d) for d in list_dict]
    return {k: [x[k] for x in flat_list_dict] for k in flat_list_dict[0]}


# https://stackoverflow.com/questions/6027558/flatten-nested-dictionaries-compressing-keys
def flatten(d, parent_key="", sep="."):
    """Flatten dictionary."""
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, MutableMapping):
            items.extend(flatten(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)
