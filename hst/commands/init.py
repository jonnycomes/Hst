from pathlib import Path


def run(repo_dir: str = ".hst"):
    """
    Initialize a new repository.
    """
    repo_path = Path(repo_dir)
    repo_path_already_exists = repo_path.exists()

    # Create the repo directory
    repo_path.mkdir(exist_ok=True)

    # Create the HEAD file
    head_file = repo_path / "HEAD"
    if not head_file.exists():
        head_file.write_text("ref: refs/heads/main\n")

    # Create the description file
    description_file = repo_path / "description"
    if not description_file.exists():
        description_file.write_text(
            "Unnamed repository; edit this file 'description' to name the repository.\n"
        )

    # Create the config file
    config_file = repo_path / "config"
    if not config_file.exists():
        config_file.write_text(
            "[core]\n"
            "\trepositoryformatversion = 0\n"
            "\tfilemode = true\n"
            "\tbare = false\n"
            "\tlogallrefupdates = true\n"
            "\tignorecase = true\n"
            "\tprecomposeunicode = true\n"
        )

    # Create some empty subdirectories
    for subdir in ["hooks", "info", "objects", "refs"]:
        (repo_path / subdir).mkdir(exist_ok=True)

    # Create ref subdirectories
    for subdir in ["heads", "tags"]:
        (repo_path / "refs" / subdir).mkdir(exist_ok=True)

    # Create objects subdirectories
    for subdir in ["info", "pack"]:
        (repo_path / "objects" / subdir).mkdir(exist_ok=True)

    # Create the info/exclude file (it's like a local .gitignore)
    exclude_file = repo_path / "info/exclude"
    if not exclude_file.exists():
        exclude_file.touch()

    # Intentionally not creating files in hooks dir. Maybe later.

    if repo_path_already_exists:
        print(f"Reinitialized existing Hst repository in {repo_path.resolve()}/")
    else:
        print(f"Initialized empty Hst repository in {repo_path.resolve()}/")
