import os
import os.path
import datetime
import config
import select
import subprocess

import logging
logger = logging.getLogger("builder")

class BuildError(Exception): pass
class ExecutionError(BuildError): pass


################################################################################
class AbstractBuildObject(object):
    _builder = None

    ############################################################################
    def __init__(self, name, version, filename, url = [], dependencies = [], patch = None):
        self.name           = name
        self.version        = version
        self.filename       = filename
        self.dependencies   = dependencies
        self.url            = url
        self.patchfile      = patch

        assert(self._builder is not None)

        self._builder.register(self)
    
    ############################################################################
    def __repr__(self):
        mstr = "<%s (%s)" % (self.name, self.filename)
        if self.patchfile and self.isPatch():
            mstr += " [ Patched ]"
        if self.isConfigure():
            mstr += " [ Configured ]"
        if self.isBuild():
            mstr += " [ Built ]"
        if self.isInstalled():
            mstr += " [ Installed ]"
        mstr += ">"
        return mstr
    
    ############################################################################
    @staticmethod
    def setBuilder(builder):
        AbstractBuildObject._builder = builder

    ############################################################################
    def build(self):
        """

        Abstract build object!
        """
        raise BuildError("Can't build an abstract BuildObject :)")
   
    ############################################################################
    def patch(self):
        if not self.patchfile:
            return True

        if self.isPatch():
            print "%s already patched..." % (self)
            return True
        
        if not self.check_dependencies("patch"):
            logger.error("Dependency check failed for %s. Can't continue." % (self))
            return False
        
        if not self.hasDistFile(self.patchfile):
            logger.info("Downloading patch file %s" % (self.patchfile))
            self.getDistFile(self.patchfile)
        
        filename = os.path.join(self._builder.distfiles, self.patchfile)
        self.goto()
        try:
            self.execute("%s -p0 < %s" % (config.PATCH, filename))
        except:
            self._setPatchOk(False)
            raise
        
        self._setPatchOk()

 
    ############################################################################
    def check_dependencies(self, action):
        def getCheckMethod(obj, action):
            if action == "install":
                action = "installed"
            return getattr(obj, "is%s" % (action.capitalize()))
        to_build = []
        
        for dep in self.dependencies:
            ## Resolve the dependecy in the builder
            obj = self._builder.getObject(dep)
            if not obj:
                logger.error("Dependency %s not found. Check your configuration." % (dep))
                return False
            if not getCheckMethod(obj, action)():
                to_build.append(obj)

        for dep in to_build:
            try:
                getattr(dep, action)()
            except BuildError:
                print "I Can't continue building myself, as the dependency %s don't wanna %s :)" % (dep, action)
                return False
        
        return True
    
    ############################################################################
    def getRepository(self):
        return "%s-%s" % (self.name, self.version)

    ############################################################################
    def getBuildPath(self):
        return os.path.join(self._builder.buildroot, self.getRepository())

    ############################################################################
    def isBuild(self):
        return self._isFile(".built")

    ############################################################################
    def isInstalled(self):
        return self._isFile(".installed")

    ############################################################################
    def isPatch(self):
        return self._isFile(".patched")

    ############################################################################
    def isConfigure(self):
        return self._isFile(".configured")

    ############################################################################
    def _isFile(self, file):
        try:
            f = open(os.path.join(self.getBuildPath(), file), "r")
        except IOError:
            return False

        f.close()
        return True
    
    ############################################################################
    def _setInstallOk(self, ok = True):
        self._setFile(".installed", ok)

    ############################################################################
    def _setPatchOk(self, ok = True):
        self._setFile(".patched", ok)

    ############################################################################
    def _setBuildOk(self, ok = True):
        self._setFile(".built", ok)

    ############################################################################
    def _setConfigureOk(self, ok = True):
        self._setFile(".configured", ok)
    
    ############################################################################
    def _setFile(self, file, ok):
        if ok:
            try:
                f = open(os.path.join(self.getBuildPath(), file), "w")
            except:
                print "Unable to create the %s file for %s." % (file, self.getBuildPath())
            f.write("%s" % (datetime.datetime.now()))
            f.close()
        else:
            try:
                os.unlink(os.path.join(self.getBuildPath(), file))
            except OSError: pass

    ############################################################################
    def clean(self):
        command = "rm -rf %s" % (self.getBuildPath())
        try:
            self.execute(command)
        except:
            print "Unable to cleanup %s: %s" % (self, command)
            raise
    
    ############################################################################
    def execute(self, command):
        myenv = os.environ
        try:
            myenv["CPPFLAGS"] = "%s -I%s" % (myenv["CPPFLAGS"] or "", os.path.join(os.getcwd(), "include"))
        except KeyError:
            myenv["CPPFLAGS"] = "-I%s" % (os.path.join(config.PREFIX, "include"))

        try:
            myenv["LDFLAGS"] = "%s -L%s" % (myenv["LDFLAGS"] or "", os.path.join(os.getcwd(), "lib"))
        except KeyError:
            myenv["LDFLAGS"] = "-L%s" % (os.path.join(config.PREFIX, "lib"))

        try:
            myenv["LD_LIBRARY_PATH"] = "%s:%s" % (myenv["LD_LIBRARY_PATH"] or "", os.path.join(os.getcwd(), "lib"))
        except KeyError:
            myenv["LD_LIBRARY_PATH"] = "%s" % (os.path.join(config.PREFIX, "lib"))

        #logger.info("Will execute %s" % (command))
        print("Will execute %s" % (command, ))
        p = subprocess.Popen(command,
                             bufsize = 0,
                             stdin   = subprocess.PIPE,
                             stdout  = subprocess.PIPE,
                             stderr  = subprocess.PIPE,
                             close_fds = True,
                             shell  = True,
                             env    = myenv)

        stdin, stdout, stderr = (p.stdin, p.stdout, p.stderr)
        stdin.close()
        if not config.VERBOSE:
            (rlst, wlst, xlst) = select.select([stdout, stderr], [], [], 0.1)
            if stdout in rlst:
                out = stdout.read()
            else:
                out = ""

            if stderr in rlst:
                err = stderr.read()
            else:
                err = ""

        else:
            err = ""
            while 1:
                (rlst, wlst, xlst) = select.select([stdout, stderr], [], [], 0.1)
                if stdout in rlst:
                    out = stdout.readline()
                    if not out:
                        break
                    else:
                        print out,

                if stderr in rlst:
                    lerr = stderr.readline()
                    err += lerr
        
        ## NOT REENTRANT !!!!
        pid = p.pid
        exit_code = p.wait()

        if exit_code != 0:
            logger.error("Error executing `%s':\n%s\nExit code was: %s (pid %s)" % (command, err, exit_code, pid))
            logger.debug("Complete output: %s" % (out))
            raise ExecutionError(err)

    ############################################################################ 
    def extract(self): 
        logger.info("Extracting %s to %s" % (self, self._builder.buildroot)) 
        os.chdir(self._builder.buildroot) 
        filename = os.path.join(self._builder.distfiles, self.filename) 
        if filename.endswith("tar.gz") or filename.endswith(".tgz"): 
            ## GZIP Tarball 
            command = "tar xvzf %s" % (filename) 
        elif filename.endswith("tar.bz2") or filename.endswith("tbz2"): 
            ## BZIP2 Tarball 
            command = "tar xvjf %s" % (filename) 
         
        self.execute(command)

    ############################################################################
    def goto(self):
        os.chdir(self.getBuildPath())

    ############################################################################
    def hasDistFile(self, file = None):
        if not file:
            file = self.filename
        filename = os.path.join(self._builder.distfiles, file)
        return os.path.isfile(filename)

    ############################################################################
    def getDistFile(self, file = None):
        if not file:
            file = self.filename

        filename = os.path.join(self._builder.distfiles, file)
        
        def getURL(url, filename):
            if url.endswith("/"):
                return "%s%s" % (url, filename)
            else:
                return "%s/%s" % (url, filename)

        if self.hasDistFile(file):
            return
       
        for url in self.url:
            try:
                command = "%s %s -O%s" % (config.WGET, getURL(url, file), filename)
                self.execute(command)
            except ExecutionError, err:
                os.unlink(filename)
                logger.warning("Error message from wget: %s" % (err))
                logger.warning("Unable to wget %s. Trying another URL if exists..." % (getURL(url, file)))
            else:
                break
    
    ############################################################################
    def getCflags(self):
        return ""

    
################################################################################
class SimpleBuildObject(AbstractBuildObject):
    """

    ./configure --prefix= && make
    """

    ############################################################################
    def getConfigureCommand(self):
        return "./configure --prefix=%s" % (config.PREFIX)
    
    ############################################################################
    def getMakeCommand(self):
        return "%s %s" % (config.MAKE, config.GMAKE_FLAGS)

    ############################################################################
    def configure(self):
        if self.isConfigure():
            print "%s already configured..." % (self)
            return True
        
        if not self.check_dependencies("configure"):
            logger.error("Dependency check failed for %s. Can't continue." % (self))
            return False

        self.goto()

        try:
            self.execute(self.getConfigureCommand())
        except:
            self._setConfigureOk(False)
            raise
        self._setConfigureOk()    

    ############################################################################
    def build(self):
        if not self.isConfigure():
            print "Can't build %s: not configured." % (self)
            return False

        if self.isBuild():
            print "%s already built..." % (self)
            return True
        
        self.check_dependencies("build")
        self.goto()
        
        command = self.getMakeCommand()

        cflags = self.getCflags()
        if cflags:
            command += " CFLAGS=%s" % (cflags, )

        try:
            self.execute(command)
        except:
            self._setBuildOk(False)
            raise
        self._setBuildOk()
        return True
    
    ############################################################################
    def install(self):
        if self.isInstalled():
            print "%s already installed..." % (self)
            return True
        
        if not self.check_dependencies("install"):
            logger.error("Dependency check failed for %s. Can't continue." % (self))
            return False

        self.goto()
        try:
            self.execute("%s install" % (config.MAKE))
        except:
            self._setInstallOk(False)
            raise
        
        self._setInstallOk()

################################################################################
class PythonBuildObject(AbstractBuildObject):
    """

    python setup.py build
    python setup.py install
    """
    ############################################################################
    def __init__(self, name, version, filename, url = [], dependencies = [], builddir = None, patch = None):
        AbstractBuildObject.__init__(self, name, version, filename, url, dependencies, patch = patch)
        self.builddir = builddir

    ############################################################################
    def getBuildPath(self):
        if self.builddir:
            return os.path.join(self._builder.buildroot, self.getRepository(), self.builddir)
        else:
            return AbstractBuildObject.getBuildPath(self)

    ############################################################################
    def _isFile(self, file):
        return AbstractBuildObject._isFile(self, "python.%s" % (file, ))

    ############################################################################
    def _setFile(self, file, ok = True):
        return AbstractBuildObject._setFile(self, "python.%s" % (file, ), ok)

    ############################################################################
    def isConfigure(self):
        return True
     
    ############################################################################
    def configure(self):
        pass

    ############################################################################
    def build(self):
        if self.isBuild():
            print "%s already built..." % (self)
            return True
        
        if not self.check_dependencies("build"):
            logger.error("Dependency check failed for %s. Can't continue." % (self))
            return False
        self.goto()

        try:
            self.execute("%s setup.py build" % (config.PYTHON_BIN))
        except:
            self._setBuildOk(False)
            raise
        self._setBuildOk()

    ############################################################################
    def install(self):
        if self.isInstalled():
            print "%s already installed..." % (self)
            return True
        
        if not self.check_dependencies("install"):
            logger.error("Dependency check failed for %s. Can't continue." % (self))
            return False
        self.goto()
        try:
            self.execute("%s setup.py install --prefix=%s" % (config.PYTHON_BIN, config.PREFIX))
        except:
            self._setInstallOk(False)
            raise
        
        self._setInstallOk()

################################################################################
class PostgreSQLBuildObject(SimpleBuildObject):
    """

    For PostgreSQL 8.x
    """
    ############################################################################ 
    def getConfigureCommand(self):
        return "%s %s" % (SimpleBuildObject.getConfigureCommand(self), "--enable-thread-safety")

################################################################################
class BZIP2BuildObject(SimpleBuildObject):
    ############################################################################
    def isConfigure(self):
        return True
     
    ############################################################################
    def configure(self):
        pass

    ############################################################################
    def getCflags(self):
        return "-fPIC"

    ############################################################################
    def install(self):
        if self.isInstalled():
            print "%s already installed..." % (self)
            return True
        
        if not self.check_dependencies("install"):
            logger.error("Dependency check failed for %s. Can't continue." % (self))
            return False
        self.goto()
        try:
            self.execute("%s install PREFIX=%s" % (config.MAKE, config.PREFIX))
            self.execute("%s -f Makefile-libbz2_so PREFIX=%s" % (config.MAKE, config.PREFIX))
            self.execute("cp libbz2.so* %s" % (os.path.join(config.PREFIX, "lib")))
        except:
            self._setInstallOk(False)
            raise
        
        self._setInstallOk()


################################################################################
class ComplexBuildObject(SimpleBuildObject):
    """

    ./configure --prefix= --truc=1 --bidule=2 ... && make ${make_flags}
    """
    ############################################################################
    def __init__(self, name, version, filename, url = [], dependencies = [],
                       configureArgs = "", makeArgs = "", override_makeflags = False, patch = None):
        SimpleBuildObject.__init__(self, name, version, filename, url, dependencies, patch = patch)
        self._makeArgs      = makeArgs
        self._configureArgs = configureArgs
        self._override_makeflags = override_makeflags

    ############################################################################
    def getConfigureCommand(self):
        configureString = "./configure --prefix=%s" % (config.PREFIX)
        if self._configureArgs:
            configureString += " %s" % (self._configureArgs)
        return configureString

    ############################################################################
    def getMakeCommand(self):
        commandString = "%s" % (config.MAKE)
        if not self._override_makeflags:
            commandString += " %s" % (config.GMAKE_FLAGS)
        
        if self._makeArgs:
            commandString += " %s" % (self._makeArgs)
        return commandString

################################################################################
class QtBuildObject(ComplexBuildObject):
    """

    For Qt 3.3
    """

    ############################################################################
    def getConfigureCommand(self):
        os.path.join(config.PREFIX, "include")
        configureString = "./configure -prefix %s -I%s -I/usr/include/freetype2 -I/usr/include/xorg -I/usr/include/X11 -L%s -L/usr/lib/i386-linux-gnu" % (config.PREFIX, os.path.join(config.PREFIX, "include"), os.path.join(config.PREFIX, "lib"))
        if self._configureArgs:
            configureString += " %s" % (self._configureArgs)
        return configureString

################################################################################
class PopplerBuildObject(ComplexBuildObject):
    """

    Qt Style (ex: polymer)
    """
    
    ############################################################################
    def configure(self):
        os.environ["QTINC"] = os.path.join(config.PREFIX, "include")
        os.environ["QTLIB"] = os.path.join(config.PREFIX, "lib")
        ComplexBuildObject.configure(self)

    ############################################################################
    def build(self):
        os.environ["QTLIB"] = os.path.join(config.PREFIX, "lib")
        os.environ["QTINC"] = os.path.join(config.PREFIX, "include")
        ComplexBuildObject.configure(self)

################################################################################
class QStyleBuildObject(ComplexBuildObject):
    """

    Qt Style (ex: polymer)
    """
    
    ############################################################################
    def configure(self):
        os.environ["QTDIR"] = config.PREFIX
        ComplexBuildObject.configure(self)

    ############################################################################
    def build(self):
        os.environ["QTDIR"] = config.PREFIX
        ComplexBuildObject.configure(self)

################################################################################
class PyQtBuildObject(ComplexBuildObject):
    """

    python confugure.py
    make
    make install
    """

    ############################################################################
    def getConfigureCommand(self):
        configureString = "python configure.py"
        if self._configureArgs:
            configureString += " %s" % (self._configureArgs)
        return configureString

################################################################################
class TCLBuildObject(ComplexBuildObject):
    """

    TCL Needs to ./configure un unix/ directory
    """

    ############################################################################
    def getRepository(self):
        return "%s%s" % (self.name, self.version)

    ############################################################################
    def getBuildPath(self):
        return os.path.join(self._builder.buildroot, self.getRepository(), "unix")

class SambaBuildObject(ComplexBuildObject):
    """

    Samba
    """
    ############################################################################
    def getRepository(self):
        return os.path.join("%s-%s" % (self.name, self.version), "source3")

