#!/usr/bin/env python

import logging
import os.path
import sys

## Basic logging configuration
logging.basicConfig()

from buildobj import *
import builder
## Build clarilab :)

userpath = os.path.expanduser("~")
basepath = os.getcwd()

if "--prefix" in sys.argv:
    config.PREFIX = sys.argv[sys.argv.index("--prefix")+1]
    config.PYTHON_BIN = os.path.join(config.PREFIX, "bin", "python")

# Need to make links in /usr/X11R6
if not os.path.exists("/usr/X11R6"):
    os.mkdir("/usr/X11R6")
    os.symlink("/usr/include/X11", "/usr/X11R6/include")

print "Config PREFIX: %s" % (config.PREFIX,)

builder = builder.Builder(buildroot = os.path.join(basepath, "buildroot"),
                  distfiles = os.path.join(basepath, "distfiles"))
AbstractBuildObject.setBuilder(builder)

if __name__ == "__main__":
    import sys
    if "--full" in sys.argv:
        ComplexBuildObject("ncurses",
            version         = "5.9",
            filename        = "ncurses-5.9.tar.gz",
            url             = config.CLARILAB_MIRROR,
            configureArgs   = "--enable-shared",
            makeArgs        = "CFLAGS=-fPIC",
            dependencies    = [],
        )

        ComplexBuildObject("readline",
            version         = "6.2",
            filename        = "readline-6.2.tar.gz",
            url             = config.CLARILAB_MIRROR,
            configureArgs   = "--with-curses",
            makeArgs        = "CFLAGS=-fPIC -j1",
            dependencies    = [ "ncurses", ],
        )

        ComplexBuildObject("zlib",
            version         = "1.2.7",
            filename        = "zlib-1.2.7.tar.gz",
            url             = config.CLARILAB_MIRROR,
            configureArgs   = "--shared",
            makeArgs        = "CFLAGS=-fPIC",
            dependencies    = [],
        )

        BZIP2BuildObject("bzip2",
            version         = "1.0.6",
            filename        = "bzip2-1.0.6.tar.gz",
            url             = config.CLARILAB_MIRROR,
            dependencies    = [],
        )
        ComplexBuildObject("Python",
            version         = "2.7.3",
            filename        = "Python-2.7.3.tar.bz2",
            url             = config.CLARILAB_MIRROR,
            dependencies    = [ "bzip2", "zlib" ],
            configureArgs   = "--enable-unicode=ucs4 --with-system-expat --with-system-ffi --with-fpectl --enable-ipv6",
        )
        PythonBuildObject("Python", 
            version         = "2.7.3",
            filename        = "Python-2.7.3.tar.bz2",
            url             = config.CLARILAB_MIRROR,
            dependencies    = [ "Python", "zlib", "bzip2" ],
        )
        ## PNG Graphics
        SimpleBuildObject("libpng",
            version        = "1.2.49",
            filename       = "libpng-1.2.49.tar.gz",
            url            = config.CLARILAB_MIRROR,
            dependencies   = [],
        )

        ## JPG Graphics
        ComplexBuildObject("jpeg",
            version        = "8d",
            filename       = "jpegsrc.v8d.tar.gz",
            url            = config.CLARILAB_MIRROR,
            dependencies   = [],
            configureArgs  = "--enable-shared",
        )

        ## Python Imaging
        PythonBuildObject("Imaging",
            version         = "1.1.7",
            filename        = "Imaging-1.1.7.tar.gz",
        #    patch           = "Imaging-1.1.7.patch",
            url             = config.CLARILAB_MIRROR,
            dependencies    = ["Python", "libpng", "jpeg"],
        )
        ## Python Imaging (sane)
        PythonBuildObject("Imaging",
            version         = "1.1.7",
            filename        = "Imaging-1.1.7.tar.gz",
            url             = config.CLARILAB_MIRROR,
            dependencies    = ["Python", "Imaging"],
            builddir        = "Sane",
        )
 
    ## Qt
    QtBuildObject("qt-x11-free",
                 version          = "3.3.8d",
                 filename         = "qt-x11-free-3.3.8d.tar.gz",
#                 patch            = "qt-x11-free-3.3.8d.patch",
                 url              = config.CLARILAB_MIRROR,
                 configureArgs    = "-qt-gif -thread -xft -xshape -system-zlib -system-libpng -disable-opengl -I/usr/include/freetype2 -I/usr/include/X11 -v -no-exceptions -fast -shared",
    )

    PopplerBuildObject("poppler",
        version         = "0.12.4",
        filename        = "poppler-0.12.4.tar.gz",
        url             = config.CLARILAB_MIRROR,
        configureArgs   = "--enable-zlib --disable-libopenjpeg --disable-cairo-output --disable-poppler-glib --disable-gdk --disable-poppler-qt4 --disable-abiword-output --disable-cms --enable-poppler-qt",
    )

    ## PyQt
    PyQtBuildObject("sip",
        version         = "4.13.3",
        filename        = "sip-4.13.3.tar.gz",
        url             = config.CLARILAB_MIRROR,
        configureArgs   = "-d %s -b %s -e %s -v %s" % (
            os.path.join(config.PREFIX, "lib", "python%d.%d" % (
                sys.version_info.major, sys.version_info.minor), "site-packages"),
            os.path.join(config.PREFIX, "bin"),
            os.path.join(config.PREFIX, "include"),
            os.path.join(config.PREFIX, "share", "sip"),
        ),
        dependencies    = ["qt-x11-free"],
    )
    PyQtBuildObject("PyQt-x11-gpl",
        version         = "3.18.1",
        filename        = "PyQt-x11-gpl-3.18.1.tar.gz",
        patch           = "PyQt-x11-gpl-3.18.1.patch",
        url             = config.CLARILAB_MIRROR,
        configureArgs   = "-q %s -j8 -v %s -d %s -b %s" % (
            config.PREFIX,
            os.path.join(config.PREFIX, "share", "sip"),
            os.path.join(config.PREFIX, "lib", "python%d.%d" % (
                sys.version_info.major, sys.version_info.minor), "site-packages"),
            os.path.join(config.PREFIX, "bin"),
        ),
        dependencies    = ["qt-x11-free", "sip"],
    )
   
    ## Polymer Qt Style
    QStyleBuildObject("polymer",
        version        = "0.3.2",
        filename       = "polymer-0.3.2.tar.gz",
        url            = config.CLARILAB_MIRROR,
        dependencies   = ["qt-x11-free"],
        configureArgs  = "--with-qt=%s --x-includes=%s" % (config.PREFIX, os.path.join(config.PREFIX, "include")),
    )
    builder.build()
