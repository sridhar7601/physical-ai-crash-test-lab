"""Subcommand dispatch: export | merge."""

import sys

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "merge":
        from .yolo_dataset import main_merge
        raise SystemExit(main_merge(sys.argv[2:]))
    from .yolo_dataset import main
    raise SystemExit(main(sys.argv[1:]))
