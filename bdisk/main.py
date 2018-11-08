#!/usr/bin/env python3

import argparse
import confparse  # LOCAL

"""The primary user interface for BDisk. If we are running interactively,
parse arguments first, then initiate a BDisk session."""

def parseArgs():
    args = argparse.ArgumentParser(description = ('An easy liveCD creator '
                                                  'built in python. Supports '
                                                  'hybrid ISOs/USB, iPXE, and '
                                                  'UEFI.'),
                                   epilog = ('https://git.square-r00t.net'))
    return(args)

def run(cfg):
    cfg = confparse.Conf(cfg, validate_cfg = True)
    cfg.parse_all()


def run_interactive():
    args = vars(parseArgs().parse_args())
    args['profile'] = {}
    for i in ('name', 'id', 'uuid'):
        args['profile'][i] = args[i]
        del(args[i])
    run(args)
    return()

if __name__ == '__main__':
    main()
