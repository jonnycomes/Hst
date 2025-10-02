import sys
from hst.commands import init, add, commit, branch

def main():
    cmnds = ["init", "add", "commit", "branch"]

    if len(sys.argv) < 2 or sys.argv[1] not in cmnds:
        print(f"Usage: hst [{'|'.join(cmnds)}]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "init":
        init.run()
    elif command == "add":
        if len(sys.argv) < 3:
            print(f"Usage: hst add <path> [<path> ...]")
            sys.exit(1)
        add.run(sys.argv[2:])
    elif command == "commit":
        commit.run(sys.argv[2:])
    elif command == "branch":
        branch.run(sys.argv[2:])
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
