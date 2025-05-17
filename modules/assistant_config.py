import os
import yaml
from dpath import util as dpath_util

DEFAULT_CONFIG_PATH = "assistant_config.yml"


def get_config(dot_path_key: str, config_path: str = DEFAULT_CONFIG_PATH) -> str:
    """
    Load a field from the YAML config file using dot notation path.

    Args:
        dot_path_key: The key path to look up in the config (e.g. 'parent.child.key')
        config_path: Path to the YAML config file, defaults to assistant_config.yml

    Returns:
        str: The value for the requested key path

    Raises:
        FileNotFoundError: If config file doesn't exist
        KeyError: If key path not found in config
    """
    # Get absolute path from current working directory
    abs_config_path = os.path.join(os.getcwd(), config_path)

    if not os.path.exists(abs_config_path):
        raise FileNotFoundError(f"Config file not found at {abs_config_path}")

    with open(abs_config_path) as f:
        config = yaml.safe_load(f)

    try:
        return dpath_util.get(config, dot_path_key, separator=".")
    except KeyError:
        raise KeyError(f"Key path '{dot_path_key}' not found in config")


def set_config(dot_path_key: str, value: any, config_path: str = DEFAULT_CONFIG_PATH):
    """
    Set a field in the YAML config file using dot notation path.

    Args:
        dot_path_key: The key path to set in the config (e.g. 'parent.child.key')
        value: The value to set.
        config_path: Path to the YAML config file, defaults to assistant_config.yml

    Raises:
        FileNotFoundError: If config file doesn't exist
        KeyError: If key path cannot be created or found in config
    """
    abs_config_path = os.path.join(os.getcwd(), config_path)

    if not os.path.exists(abs_config_path):
        raise FileNotFoundError(f"Config file not found at {abs_config_path}")

    with open(abs_config_path, 'r') as f:
        config = yaml.safe_load(f)

    if config is None:
        config = {}

    try:
        # Use new_keys=True to create keys if they don't exist
        dpath_util.set(config, dot_path_key, value, separator=".", new_keys=True)
    except Exception as e:
        # Catch broader exception as dpath.util.set can raise various errors
        raise KeyError(f"Could not set key path '{dot_path_key}' in config: {e}")

    with open(abs_config_path, 'w') as f:
        yaml.safe_dump(config, f)


def get_config_file(config_path: str = DEFAULT_CONFIG_PATH) -> str:
    """
    Get the config file as a string.
    """
    with open(config_path, "r") as f:
        return f.read()
