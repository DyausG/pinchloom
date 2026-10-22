"""CLI entry point for Pinchloom, adapted from AeroPuzzle."""

import argparse
from aeropuzzle import __version__


def main():
    parser = argparse.ArgumentParser(
        prog="aeropuzzle",
        description="Pinchloom - Gesture Arcade. A calibrated picture-swap game adapted from AeroPuzzle.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    # Parse known args so we can still pass through any future flags
    parser.add_argument('--mouse',action='store_true',help='Explicit mouse fallback: vision disabled')
    parser.add_argument('--grid',type=int,choices=[2,3],default=3)
    parser.add_argument('--camera',type=int,default=0)
    args=parser.parse_args()

    # Launch the game
    from aeropuzzle.app import main as run_game
    run_game(mouse=args.mouse,grid_size=args.grid,camera_index=args.camera)


if __name__ == "__main__":
    main()
