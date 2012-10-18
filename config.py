import os

## This file describe global configuration for the build system.
## If PATH is None, then the PATH environment variable is not overriden.
PATH = None

## Don't forget crle :)
CC = "gcc" # -m64"

## gMake flags (eg. -j8)
GMAKE_FLAGS = "-j4"

## Where to install our stuff ?
PREFIX = "/clarilab"

## Defautt is to use our python!
PYTHON_BIN = os.path.join(PREFIX, "bin", "python")

MAKE = "/usr/bin/make"

PATCH = "/usr/bin/patch"

MIRROR = [ "http://path/to/mirror/", ]

WGET = "/usr/bin/wget"

## Should I show all executed stuff ?
VERBOSE = True

## This configuration should not been modified unless you really know what you are doing !
