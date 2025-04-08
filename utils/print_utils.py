# import sys
# import os

# sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
# sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# from app.src.logger import print_and_log


def prRed(text):
    # print_and_log(text,False)
    print("\033[91m{}\033[00m".format(text))


def prGreen(text):
    # print_and_log(text, False)
    print("\033[92m{}\033[00m".format(text))


def prYellow(text):
    # print_and_log(text, False)
    print("\033[93m{}\033[00m".format(text))


def prLightPurple(text):
    # print_and_log(text, False)
    print("\033[94m{}\033[00m".format(text))


def prPurple(text):
    # print_and_log(text, False)
    print("\033[95m{}\033[00m".format(text))


def prCyan(text):
    # print_and_log(text, False)
    print("\033[96m{}\033[00m".format(text))


def prLightGray(text):
    # print_and_log(text, False)
    print("\033[97m{}\033[00m".format(text))


def prBlack(text):
    # print_and_log(text, False)
    print("\033[98m{}\033[00m".format(text))
