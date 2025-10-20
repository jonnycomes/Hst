import sys
from hst.commands import (
    init,
    add,
    commit,
    branch,
    switch,
    status,
    restore,
    log,
    diff,
    merge,
    clone,
    remote,
    push,
    pull,
    fetch,
    rebase,
)


def main():
    cmnds = [
        "init",
        "add",
        "commit",
        "branch",
        "switch",
        "status",
        "restore",
        "log",
        "diff",
        "merge",
        "clone",
        "remote",
        "push",
        "pull",
        "fetch",
        "rebase",
    ]

    if len(sys.argv) < 2 or sys.argv[1] not in cmnds:
        print(f"Usage: hst [{'|'.join(cmnds)}]")
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]

    if command == "init":
        init.run()
    elif command == "add":
        add.run(args)
    elif command == "commit":
        commit.run(args)
    elif command == "branch":
        branch.run(args)
    elif command == "switch":
        switch.run(args)
    elif command == "status":
        status.run(args)
    elif command == "restore":
        restore.run(args)
    elif command == "log":
        log.run(args)
    elif command == "diff":
        diff.run(args)
    elif command == "merge":
        merge.run(args)
    elif command == "clone":
        clone.run(args)
    elif command == "remote":
        remote.run(args)
    elif command == "push":
        push.run(args)
    elif command == "pull":
        pull.run(args)
    elif command == "fetch":
        fetch.run(args)
    elif command == "rebase":
        rebase.run(args)
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
