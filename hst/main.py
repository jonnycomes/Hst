import sys
from hst.commands import init


def main():
    cmnds = ["init"]

    if len(sys.argv) < 2:
        print(f"Usage: hst [{'|'.join(cmnds)}]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "init":
        init.run()
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
