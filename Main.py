import logging

import TableWorld_Gui


def main():
    logging.basicConfig(filename='table-world.log', level=logging.INFO)
    TableWorld_Gui.initialise_window()


if __name__ == '__main__':
    main()
