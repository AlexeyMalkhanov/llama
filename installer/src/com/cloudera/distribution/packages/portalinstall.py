# (c) Copyright 2008 Cloudera, Inc.
#
# module: com.cloudera.distribution.packages.portalinstall
#
# Defines the ToolInstall instance that installs the web portal

from com.cloudera.distribution.installerror import InstallError
from com.cloudera.distribution.toolinstall import ToolInstall
from com.cloudera.distribution.constants import *

import com.cloudera.distribution.arch as arch
import com.cloudera.util.output as output
import com.cloudera.tools.shell as shell

class PortalInstall(ToolInstall):

  def __init__(self, properties):
    ToolInstall.__init__(self, "Portal", properties)

    # need Hadoop because the portal source code
    # is part of the Hadoop package
    self.addDependency("Hadoop")

  def precheck(self):
    """ If anything must be verified before we even get going, check those
        constraints in this method """

    # check to see if htdocs exist
    htdocs = self.getPortalDest()
    files = os.listdir(htdocs)
    if len(files) != 0:
      overwrite_flag = self.properties.getProperty(OVERWRITE_HTDOCS_KEY, \
                                        OVERWRITE_HTDOCS_DEFAULT)

      # if they do exist and we're in unattended mode, break with errors
      if self.isUnattended() and not overwrite_flag:
        output.printlnVerbose("Failing because htdocs will not be overwritten")
        output.printlnInfo("""
Your htdocs (%(htdocs)s) folder has files in it.  This installer will add
files to this directory and possibly overwrite data without backup.  Please
either move your files elsewhere or erase them completely if they are
the default set of documents for Apache, Lighttpd, etc.  You can also
run this script with the --overwrite-htdocs option.
""" % {'htdocs': htdocs,
       })
        raise InstallError(htdocs + " has files; please move or erase them")
      # otherwise, ask the user what to do
      elif not overwrite_flag:
        output.printlnVerbose("Asking the user if we should overwrite htdocs")
        output.printlnInfo("""
You already have an htdocs folder, and there are files and directories in this
folder.  The htdocs folder is:
    %(htdocs)s
This script will potentially overwrite these files.  Should the tool
proceed and potentially ovewrite these files?  If you specify "no," then you
will have to move these htdocs elsewhere.
""" % {'htdocs': htdocs,
       })
        overwrite = False
        while True:
          answer = prompt.getString("(y or n):")
          if answer.lower().startswith('y'):
            overwrite = True
            break
          elif answer.lower().startswith('n'):
            overwrite = False
            break
        if not overwrite:
          raise InstallError(htdocs + " has files; please move or erase them")

  def install(self):
    """ Run the installation itself. """

    # the portal is only installed on the NN
    if self.isMaster():
      self.install_httpd()
      self.install_portal()

  def install_httpd(self):
    """
    Installs Lighttpd with PHP5 and MySQL support. 
    Assumes MySQL is already installed
    """

    # instructions for this were taken from:
    #  FC: http://www.howtoforge.com/lighttpd_php5_mysql_fedora7
    #  Ubuntu: http://www.ubuntugeek.com/lighttpd-webserver-setup
    #                -with-php5-and-mysql-support.html

    output.printlnVerbose("Installing lighttpd-related packages")

    # install lighttpd and other required modules
    pckg = {arch.PACKAGE_MGR_DEBIAN: [
                                      "lighttpd",
                                      "php5-cgi",
                                      "php5-mysql",
                                      ],
            arch.PACKAGE_MGR_RPM: [
                                   "lighttpd",
                                   "lighttpd-fastcgi",
                                   "php-cli",
                                   "php-mysql",
                                  ],
            }
    self.installPackage(pckg)

    arch_inst = arch.getArchDetector()

    # update php and lighttpd config files
    deps_arch_dir = ""
    php_ini_dest = ""
    platform = arch_inst.getPlatform()

    output.printlnVerbose("Installing php.ini and lighttpd.conf")

    if platform == arch.PLATFORM_UBUNTU:
      deps_arch_dir = os.path.join(DEPS_PATH,
                                   "ubuntu-8.04-i386")
      php_ini_dest = "/etc/php5/cgi/php.ini"
    elif platform == arch.PLATFORM_FEDORA:
      deps_arch_dir = os.path.join(DEPS_PATH,
                                   "fedora8-i386")
      php_ini_dest = "/etc/php.ini"

    good_php_ini = os.path.abspath(
                        os.path.join(deps_arch_dir, "php.ini"))
    good_http_conf = os.path.abspath(
                        os.path.join(deps_arch_dir, "lighttpd.conf"))

    lighttpd_conf = "/etc/lighttpd/lighttpd.conf"

    ToolInstall.backupFile(php_ini_dest)
    ToolInstall.backupFile(lighttpd_conf)

    try:
      shell.shLines("cp " + good_http_conf + " " + lighttpd_conf)
    except shell.CommandError:
      raise InstallError("Could not copy a custom lighttpd configuration")

    try:
      shell.shLines("cp " + good_php_ini + " " + php_ini_dest)
    except shell.CommandError:
      raise InstallError("Could not copy a custom php.ini")

    try:
      shell.shLines("/etc/init.d/lighttpd restart")
    except shell.CommandError:
      raise InstallError("Could not restart lighttpd using /etc/init.d/lighttpd")

    output.printlnInfo("Installed lighttpd with PHP and MySQL support.")

  def install_portal(self):
    """
    Install the portal by copying to lighttpd's docroot.
    Because LogMover has already been run, the DB has
    already been bootstrapped
    """

    # get the location of the hadoop distribution
    # so we can copy the portal files from there
    hadoop_folder = self.getHadoopLocation()
    src_folder = os.path.join(hadoop_folder,
                              PORTAL_SRC_LOCATION)
    src_folder = os.path.join(src_folder,
                              "*")

    output.printlnVerbose("Copying portal files to htdocs")

    dest_folder = self.getPortalDest()
    try:
      cpLines = shell.shLines("cp -R " + src_folder + " " + dest_folder)
    except shell.CommandError:
      raise InstallError("Portal web app could not be copied to " + dest_folder)

    output.printlnInfo("Successfully installed the portal")

    jobtracker = self.properties.getProperty(JOB_TRACKER_KEY)
    namenode = self.properties.getProperty(NAMENODE_KEY)

    # just strip the port off the jobtracker
    jobtracker = self.getHost(jobtracker)

    # remove the protocol (hdfs://) along with the port
    namenode = namenode[7:]
    namenode = self.getHost(namenode)

    try:
      jt_cmd = "sed -i -e 's/jobtracker.domain/" + jobtracker + "/' " + \
                                        os.path.join(dest_folder, "index.html")

      nn_cmd = "sed -i -e 's/namenode.domain/" + namenode + "/' " + \
                                        os.path.join(dest_folder, "index.html")

      output.printlnVerbose("seding the HTDOCS/index.html file")
      lines = shell.shLines(jt_cmd)
      output.printlnVerbose(lines)
      lines = shell.shLines(nn_cmd)
      output.printlnVerbose(lines)
    except shell.CommandError:
      raise InstallError("Could not sed the portal's index.html file")

    self.updatePortalConf()

  @staticmethod
  def getHost(host_and_port):
    """Gets the host from a string host:port"""
    parts = host_and_port.split(":")
    return parts[0]

  def getHadoopLocation(self):
    """Gets the location where Hadoop is installed"""
    return os.path.join(self.getInstallBasePath(),
                        HADOOP_INSTALL_SUBDIR)

  def getPortalDest(self):
    """Gets the dest where portal will be installed"""
    arch_inst = arch.getArchDetector()
    if arch_inst.getPlatform() == arch.PLATFORM_FEDORA:
      dest_folder = LIGHTTPD_FC_HTDOCS
    elif arch_inst.getPlatform() == arch.PLATFORM_UBUNTU:
      dest_folder = LIGHTTPD_UBUNTU_HTDOCS
    else:
      raise InstallError("Your platform is not currently supported.")

    return dest_folder

  def configure(self):
    """ Run the configuration stage. This is responsible for
        setting up the config files and asking any questions
        of the user. The software is not installed yet """
    pass

  def updatePortalConf(self):
    """
    Update the portal by telling it where the hadoop-site.xml
    file is
    """

    hadoop_folder = self.getHadoopLocation()
    hadoop_site = os.path.join(hadoop_folder, "conf/hadoop-site.xml")

    portal_dest = self.getPortalDest()
    portal_conf = os.path.join(portal_dest, "hadoop-site-location")

    output.printlnVerbose("Writing location of hadoop-site.xml to portal config")

    try:
      f = open(portal_conf, 'w')
      f.write(hadoop_site)
      f.close()
    except:
      raise InstallError("Portal web app could not be configured")

    output.printlnInfo("Portal configuration updated")

  def postInstall(self):
    """ Run any post-installation activities. This occurs after
        all ToolInstall objects have run their install() operations. """
    # TODO postinstall Portal
    pass

  def verify(self):
    """ Run post-installation verification tests, if configured """
    # TODO: Verify Portal

  def getRedeployArgs(self):
    """ Provide any command-line arguments to the installer on the slaves """
    # TODO: Return anything necessary.
    return []

