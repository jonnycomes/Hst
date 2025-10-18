import sys
from hst.commands import init, add, commit, branch, switch, status, restore, log


def main():
    cmnds = ["init", "add", "commit", "branch", "switch", "status", "restore", "log"]

    if len(sys.argv) < 2 or sys.argv[1] not in cmnds:
        print(f"Usage: hst [{'|'.join(cmnds)}]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "init":
        init.run()
    elif command == "add":
        add.run(sys.argv[2:])
    elif command == "commit":
        commit.run(sys.argv[2:])
    elif command == "branch":
        branch.run(sys.argv[2:])
    elif command == "switch":
        switch.run(sys.argv[2:])
    elif command == "status":
        status.run(sys.argv[2:])
    elif command == "restore":
        restore.run(sys.argv[2:])
    elif command == "log":
        log.run(sys.argv[2:])
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
