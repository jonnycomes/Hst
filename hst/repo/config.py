import configparser
import shutil
from pathlib import Path
from typing import Dict, Optional


def get_config_path(hst_dir: Path) -> Path:
    """Get the path to the config file."""
    return hst_dir / "config"


def read_config(hst_dir: Path) -> configparser.ConfigParser:
    """Read the repository config file."""
    config = configparser.ConfigParser()
    config_path = get_config_path(hst_dir)
    if config_path.exists():
        config.read(config_path)
    return config


def write_config(hst_dir: Path, config: configparser.ConfigParser) -> None:
    """Write the repository config file."""
    config_path = get_config_path(hst_dir)
    with open(config_path, "w") as f:
        config.write(f)


def read_remotes(hst_dir: Path) -> Dict[str, str]:
    """
    Read the remotes configuration from config file.

    Returns:
        Dictionary mapping remote name to URL
    """
    config = read_config(hst_dir)
    remotes = {}

    for section_name in config.sections():
        if section_name.startswith('remote "') and section_name.endswith('"'):
            # Extract remote name from section name like 'remote "origin"'
            remote_name = section_name[8:-1]  # Remove 'remote "' and '"'
            section = config[section_name]
            if "url" in section:
                remotes[remote_name] = section["url"]

    return remotes


def write_remotes(hst_dir: Path, remotes: Dict[str, str]) -> None:
    """
    Write the remotes configuration to config file.

    Args:
        hst_dir: Path to the .hst directory
        remotes: Dictionary mapping remote name to URL
    """
    config = read_config(hst_dir)

    # Remove existing remote sections
    sections_to_remove = []
    for section_name in config.sections():
        if section_name.startswith('remote "') and section_name.endswith('"'):
            sections_to_remove.append(section_name)

    for section_name in sections_to_remove:
        config.remove_section(section_name)

    # Add new remote sections
    for name, url in remotes.items():
        section_name = f'remote "{name}"'
        config.add_section(section_name)
        config[section_name]["url"] = url
        config[section_name]["fetch"] = f"+refs/heads/*:refs/remotes/{name}/*"

    write_config(hst_dir, config)


def add_remote(hst_dir: Path, name: str, url: str) -> bool:
    """
    Add a remote to the configuration.

    Args:
        hst_dir: Path to the .hst directory
        name: Name of the remote
        url: URL/path of the remote

    Returns:
        True if added successfully, False if remote already exists
    """
    config = read_config(hst_dir)
    section_name = f'remote "{name}"'

    # Check if remote already exists
    if section_name in config:
        return False

    # Add the remote section
    config.add_section(section_name)
    config[section_name]["url"] = url
    config[section_name]["fetch"] = f"+refs/heads/*:refs/remotes/{name}/*"

    # Create the remotes directory structure
    remote_refs_dir = hst_dir / "refs" / "remotes" / name
    remote_refs_dir.mkdir(parents=True, exist_ok=True)

    write_config(hst_dir, config)
    return True


def remove_remote(hst_dir: Path, name: str) -> bool:
    """
    Remove a remote from the configuration.

    Args:
        hst_dir: Path to the .hst directory
        name: Name of the remote to remove

    Returns:
        True if removed successfully, False if remote doesn't exist
    """
    config = read_config(hst_dir)
    section_name = f'remote "{name}"'

    if section_name not in config:
        return False

    # Remove the config section
    config.remove_section(section_name)
    write_config(hst_dir, config)

    # Remove the remote refs directory
    remote_refs_dir = hst_dir / "refs" / "remotes" / name
    if remote_refs_dir.exists():
        shutil.rmtree(remote_refs_dir)

    return True


def get_remote_url(hst_dir: Path, name: str) -> Optional[str]:
    """
    Get the URL for a specific remote.

    Args:
        hst_dir: Path to the .hst directory
        name: Name of the remote

    Returns:
        URL of the remote, or None if not found
    """
    config = read_config(hst_dir)
    section_name = f'remote "{name}"'

    if section_name in config and "url" in config[section_name]:
        return config[section_name]["url"]

    return None


def list_remotes(hst_dir: Path, verbose: bool = False) -> None:
    """
    List all configured remotes.

    Args:
        hst_dir: Path to the .hst directory
        verbose: If True, show URLs as well as names
    """
    remotes = read_remotes(hst_dir)

    if not remotes:
        return

    for name, url in sorted(remotes.items()):
        if verbose:
            print(f"{name}\t{url} (fetch)")
            print(f"{name}\t{url} (push)")
        else:
            print(name)


def get_remote_refs_dir(hst_dir: Path, remote_name: str) -> Path:
    """Get the directory where remote tracking branches are stored."""
    return hst_dir / "refs" / "remotes" / remote_name
