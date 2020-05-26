#!/usr/bin/env python3
import argparse
import logging
import sys
import os
import re


def lowercase(string):
    return str(string).lower()


def snakecase(string):
    string = re.sub(r"[\-\.\s]", '_', str(string))
    if not string:
        return string
    return lowercase(string[0]) + re.sub(r"[A-Z]",
            lambda matched: '_' + lowercase(matched.group(0)), string[1:])


def spinalcase(string):
    return re.sub(r"_", "-", snakecase(string))


class Command:
    usage = "<undefined>"
    description = "<undefined>"

    def __init__(self, subparsers):
        self.subparsers = subparsers
        self.command = spinalcase(self.__class__.__name__.split("Command")[1])
        self.parser = self.subparsers.add_parser(
            self.command,
            usage=self.usage,
            description=self.description)
        self.add_subparser()

    def add_subparser(self):
        raise Exception("this method should be defined in the subclass")


class CommandVispyTerm(Command):
    usage = f"{sys.argv[0]} vispy-term [OPTIONS]"
    description = "Starts an art-sci-term with vispy backend"

    def add_subparser(self):
        pass

    def run(self, args):
        from asciterm_vispy import ArtSciTermVispy
        terminal = ArtSciTermVispy(args, 1000, 1000, scale=2.5)
        terminal.run()


class CommandGlumpyTerm(Command):
    usage = f"{sys.argv[0]} glumpy-term [OPTIONS]"
    description = "Starts an art-sci-term with glumpy backend"

    def add_subparser(self):
        pass

    def run(self, args):
        from asciterm_glumpy import ArtSciTermGlumpy
        terminal = ArtSciTermGlumpy(args, 1000, 1000, scale=2.5)
        terminal.run()


class CommandKivyTerm(Command):
    usage = f"{sys.argv[0]} kivy-term [OPTIONS]"
    description = "Sends jack aaudio over network"

    def add_subparser(self):
        pass

    def run(self, args):
        from asciterm_kivy import ArtSciTermKivy
        terminal = ArtSciTermKivy(args, 1000, 1000, scale=2.5)
        terminal.run()


def run(raw_args=None):

    parser = argparse.ArgumentParser(
        usage=f"{sys.argv[0]} [OPTIONS] COMMAND",
        description="OpenGL terminal 2.0 for artists scientists and engineers",
        epilog="")
    parser.add_argument('--log-level',
                        choices=['debug', 'info', 'warn', 'error', 'fatal'],
                        default='info')
    parser.add_argument('-l', '--libvterm-path',
                        help="path to the libvterm library, otherwise we use ldconf to find it")

    subparsers = parser.add_subparsers(dest='command')

    cmd_map = {}
    for cmd in [
            CommandVispyTerm(subparsers),
            CommandGlumpyTerm(subparsers),
            CommandKivyTerm(subparsers)]:
        cmd_map[cmd.command] = cmd

    if raw_args:
        args = parser.parse_known_args(raw_args)
    else:
        args = parser.parse_known_args()

    log_level = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warn': logging.WARNING,
        'error': logging.ERROR,
        'fatal': logging.CRITICAL
    }[args[0].log_level]


    logger = logging.getLogger()
    logger.setLevel(log_level)
    for handler in logger.handlers:
        handler.setLevel(log_level)

    if args[0].command is None:
        parser.print_help()
        return 1

    cmd = cmd_map[args[0].command]
    return cmd.run(args)


if __name__ == "__main__":
    run()



