import sys
import argparse

from bbldpl_manager.bbldpl_manager import BbldplManager

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config",
        help="Path to configuration file",
        default="config.json"
    )
    parser.add_argument("--storage",
        help="Path to storage file",
        default="storage.json"
    )
    parser.add_argument("--image",
        help="Name of the Docker image to be used",
    )
    parser.add_argument("command",
        help="Command to be executed.",
        choices=["deploy", "destroy"]
    )
    args = parser.parse_args()

    manager = BbldplManager(args.image, args.config, args.storage)
    if args.command == "deploy":
        try:
            manager.deploy()
        finally:
            manager.flush_storage()
    elif args.command == "destroy":
        manager.destroy()
    else:
        print("Error: Invalid command")
        sys.exit(1)


if __name__ == "__main__":
    main()
