import os


def solve_path(path):
    # Basic functionality for now, create directories if they don't exist
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
