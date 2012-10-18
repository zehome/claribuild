import os
import os.path
import logging

import config

logger = logging.getLogger("builder")

class BuilderException(Exception): pass

################################################################################
class Builder(object):
    ############################################################################
    def __init__(self, buildroot, distfiles):
        self.builds = []

        self.buildroot = buildroot
        self.distfiles = distfiles
        
        ## Check
        if not os.path.isdir(buildroot):
            try:
                os.mkdir(buildroot)
            except OSError:
                print "%s does not exists or is not a directory." % (buildroot)
                raise BuilderException

        if not os.path.isdir(distfiles):
            try:
                os.mkdir(distfiles)
            except OSError:
                print "%s does not exists or is not a directory." % (distfiles)
                raise BuilderException

    ############################################################################
    def setEnvironnement(self):
        """

        config.PREFIX/lib must be in LD_LIBRARY_PATH
        config.PREFIX/bin must be in PATH
        """

        env_path            = os.getenv("PATH")
        env_library_path    = os.getenv("LD_LIBRARY_PATH")
        ldflags             = os.getenv("LDFLAGS")
        cflags              = os.getenv("CFLAGS")
        
        if ldflags:
            os.environ["LDFLAGS"] = "%s -L%s" % (ldflags, os.path.join(config.PREFIX, "lib"))
        else:
            os.environ["LDFLAGS"] ="-L%s" % (os.path.join(config.PREFIX, "lib"))

        if cflags:
            os.environ["CFLAGS"] = "%s -L%s" % (ldflags, os.path.join(config.PREFIX, "include"))
        else:
            os.environ["CFLAGS"] = "-I%s" % (os.path.join(config.PREFIX, "include"))

        if env_path and ":" in env_path:
            if not os.path.join(config.PREFIX, "bin") in env_path:
                newpath = "%s:%s" % (os.path.join(config.PREFIX, "bin"), env_path)
                logger.info("Setting up new environnement variable PATH: %s" % (newpath))
                os.environ["PATH"] = newpath
        else:
            newpath = "%s:%s" % (os.path.join(config.PREFIX, "bin"), env_path)
            logger.info("Setting up new environnement variable PATH: %s" % (newpath))
            os.environ["PATH"] = newpath

        if env_library_path and ":" in env_path:
            if not os.path.join(config.PREFIX, "lib") in env_library_path:
                newpath = "%s:%s" % (os.path.join(config.PREFIX, "lib"), env_library_path)
                logger.info("Setting up new environnement variable LD_LIBRARY_PATH: %s" % (newpath))
                os.environ["LD_LIBRARY_PATH"] = newpath
        else:
            newpath = "%s:%s" % (os.path.join(config.PREFIX, "lib"), env_library_path)
            logger.info("Setting up new environnement variable LD_LIBRARY_PATH: %s" % (newpath))
            os.environ["LD_LIBRARY_PATH"] = newpath
         
        os.putenv("PATH", os.environ["PATH"])
        os.putenv("LD_LIBRARY_PATH", os.environ["LD_LIBRARY_PATH"])
        os.putenv("CFLAGS", os.environ["CFLAGS"])
        os.putenv("LDFLAGS", os.environ["LDFLAGS"])

    ############################################################################
    def register(self, buildObject):
        self.builds.append(buildObject)

    ############################################################################
    def getObject(self, object_name):
        for obj in self.builds:
            if obj.name == object_name:
                return obj
        return None

    ############################################################################
    def build(self, project = "all"):
        """

        Build all registered projects, by default

        Or specify a project name, and the builder will
        build all dependencies, then the specified project :)
        """

        print "=> Building project %s" % (project)

        self.setEnvironnement()

        if project == "all":
            # Ok, I need to build all registered projects
            builds = self.builds
        else:
            builds = [ obj for obj in self.builds if obj.name == project ]

        print "Modules in this project: "
        for obj in builds: print " -> %s" % (obj)

        for obj in builds:
            print "=> Building %s" % (obj)
            
            if not obj.hasDistFile():
                print " -> Getting distfile..."
                obj.getDistFile()

            object_path = obj.getBuildPath()
            if not os.path.isdir(object_path):
                ## I should extract it
                print " -> Extracting %s" % (obj)
                obj.extract()

            print " -> patching..."
            obj.patch()
            
            print " -> configure..."
            obj.configure()
            print " -> done."
            print " -> build..."
            obj.build()
            print " -> done."
            print " -> install..."
            obj.install()
            print " -> done."

        print "=> Project %s built." % (project)
