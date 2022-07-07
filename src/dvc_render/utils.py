def list_dict_to_dict_list(list_dict):
    """Convert from list of dictionaries to dictionary of lists."""
    if not list_dict:
        return {}
    return {k: [x[k] for x in list_dict] for k in list_dict[0]}
