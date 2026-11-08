"""Download one model in its own process.

    python -m forge.download_worker <repo_id>
"""
import sys


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1 or not argv[0].strip():
        print('usage: python -m forge.download_worker <repo_id>', file=sys.stderr)
        return 2
    from forge.downloads import run_worker

    run_worker(argv[0].strip())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
