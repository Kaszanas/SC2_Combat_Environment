import typer
import logging


from sc2_combat_detector.utils import parse_subfolders


def main():
    # Run Pysc2 parser and then load the data and perform combat detection:

    logging.basicConfig()

    parse_subfolders()


if __name__ == "__main__":
    typer.run(main)
