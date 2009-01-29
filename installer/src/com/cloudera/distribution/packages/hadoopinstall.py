# (c) Copyright 2009 Cloudera, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# module: com.cloudera.distribution.packages.hadoopinstall
#
# Defines the ToolInstall instance that installs Hadoop

import pickle
import logging
import math
import os
import re
import shutil
import socket
import sys
import time

from   com.cloudera.distribution.constants import *
import com.cloudera.distribution.dnsregex as dnsregex
import com.cloudera.distribution.hadoopconf as hadoopconf
from   com.cloudera.distribution.installerror import InstallError
import com.cloudera.distribution.toolinstall as toolinstall
import com.cloudera.tools.dirutils as dirutils
import com.cloudera.tools.shell as shell
import com.cloudera.util.output as output
import com.cloudera.util.prompt as prompt

class HadoopInstall(toolinstall.ToolInstall):
  def __init__(self, properties):
    toolinstall.ToolInstall.__init__(self, "Hadoop", properties)

    self.addDependency("GlobalPrereq")

    self.configuredHadoopSiteOnline = False
    self.hadoopSiteDict = {}
    self.libLzoFound = False
    self.libBzipFound = False
    self.startedHdfs = False
    self.startedMapRed = False
    self.hadoopUser = None  # who should we run hadoop as?
    self.curUsername = None # who are we running as? (`whoami`)
    self.verified = False
    self.hdfsFormatMsg = None
    self.hadoop_log_dir = None

    self.create_ssh_key = False
    self.redist_pubkey_filename = None
    self.warn_need_ssh_keys = False


  def getPubKeyFile(self):
    """ Return the name of the hadoop user's public key file to redistribute
        during deployment, or None if there isn't any."""
    return self.redist_pubkey_filename


  def isHadoopVerified(self):
    """ return True if verification tests passed."""
    return self.verified


  def isMaster(self):
    """ Return true if we are installing on a master server, as opposed to
        a slave server."""
    return toolinstall.getToolByName("GlobalPrereq").isMaster()


  def getHadoopSiteProperty(self, propName):
    """ If the user configured hadoop-site in this tool, extract
        a property from the map the user created """
    return self.hadoopSiteDict[propName]


  def getHadoopUsername(self):
    """ Return the username we should run hadoop as. This returns the value
        of --hadoop-user. If that's not set, returns your current username
        if you're not root, or "hadoop" if you are. This user is guaranteed
        to exist locally. This field is populated in the precheckUsername()
        method. """
    return self.hadoopUser


  def isRoot(self):
    """ Return true if you're running as root. The curUsername field is
        populated in the precheckUsername() method."""
    return self.curUsername == "root"

  def getUserSwitchCmdStr(self):
    """ If we are root, or running in interactive mode, we can sudo to
        another user to run hadoop. Return the sudo cmd prefix to do so
        here if we're using a different username. Return an empty string
        if we're using the current username."""

    hadoopUser = self.getHadoopUsername()
    curUser = self.curUsername

    if self.isRoot() or (not self.isUnattended() and curUser != hadoopUser):
      return "sudo -H -u " + hadoopUser + " "
    else:
      return ""

  def kill_all_hadoop_daemons(self):
    """ Attempts to kill any/all Hadoop daemons it can find. If this is
        running as root, will kill all of them; other users will only be
        able to stop their own daemons.

        Depends on $HADOOP_PID_DIR environment variable, per Hadoop's
        bin/stop-*.sh scripts.
    """

    output.debug("Trying to stop all Hadoop services...")

    # Look at all the files in the pid dir, look for those that match
    # the regex "hadoop-(user name?)-command.pid"
    # The user-name component may actually be an arbitrary user-controlled
    # "ident string," so we're liberal about this.
    # command is one of:
    #   datanode
    #   jobtracker
    #   tasktracker
    #   secondarynamenode
    #   namenode

    pid_dir = self.properties.getProperty(HADOOP_PID_DIR_KEY, \
        HADOOP_PID_DIR_DEFAULT)

    dir_contents = os.listdir(pid_dir)

    pidfile_regex = re.compile("hadoop-.*-" \
        + "((namenode)|(datanode)|(secondarynamenode)|(jobtracker)|(tasktracker)).pid")

    # the list of pids that we couldn't kill and we think we should have.
    error_pids = []

    # the list of pids owned by other users (kill -0 returned error)
    foreign_pids = []


    for filename in dir_contents:
      m = pidfile_regex.match(filename)
      if m != None and m.start() == 0 and m.end() == len(filename):
        # Found a filename that matches that expression; pull out the component
        # name from the parentheses group.
        service = m.group(1)
        logging.debug("Found pidfile " + filename + " for service " + service)

        # convert the filename to its full path so we can open it.
        filename = os.path.join(pid_dir, filename)

        try:
          handle = open(filename)
          pid = int(handle.readline())
          handle.close()
        except ValueError:
          # line wasn't a number?
          continue
        except IOError, ioe:
          # couldn't read this? just ignore...
          output.error("Warning: could not read pidfile: " + filename)
          output.error(str(ioe))
          continue

        # determine if this pid still exists and if it is for the same command
        # that we think it is for.
        try:
          handle = open("/proc/" + str(pid) + "/cmdline")
          cmdline = handle.readline()
          # the cmdline contains nul characters between tokens here
          logging.debug("cmdline is : " + cmdline.replace(chr(0)," "))
          handle.close()
        except IOError, ioe:
          # This is a stale pidfile; the pid doesn't actually exist.
          continue

        cmdline = cmdline.lower()
        if cmdline.find("java") >= 0 and cmdline.find(service) >= 0:
          # This is an actual Hadoop daemon for this service. Let's kill it.
          logging.debug("Found hadoop daemon process")
          try:
            logging.debug("Testing pid " + str(pid) + " for killability")
            shell.sh("kill -0 " + str(pid))
            logging.debug("Seems like it should work.")
          except shell.CommandError:
            # kill -0 returned an exit status => we can't send it a signal.
            logging.debug("Could not kill -0 " + str(pid))
            foreign_pids.append(pid)
            continue

          try:
            logging.debug("Actually trying to kill pid")
            shell.sh("kill " + str(pid))
          except shell.CommandError:
            logging.debug("Kill command exited with non-zero status.")
            error_pids.append(pid)

    some_error = False

    if len(error_pids) > 0:
      logging.error("Errors were encountered killing processes:")
      for pid in error_pids:
        logging.error("  " + str(pid))
      some_error = True

    if len(foreign_pids) > 0:
      some_error = True
      logging.error("The following running Hadoop processes are owned by other users:")
      for pid in foreign_pids:
        # Determine the user who owns this process
        lines = shell.shLines("ps aux | grep \" " + str(pid) + " \"")
        process_owner = "(unknown)"
        for line in lines:
          components = line.split()
          try:
            if int(components[1]) == pid:
              process_owner = components[0]
              break
          except ValueError:
            # couldn't convert components[1] to int? not a pid.
            continue
        logging.error("  " + str(pid) + " owned by " + process_owner)

    if some_error:
      logging.error("""
Warning: All Hadoop processes could not be terminated. This may
interfere with the installation process. If errors occur, try stopping
these services and reinstalling this distribution.
""")


  def get_start_hdfs_cmd(self):
    """ Return the command to start HDFS """

    hadoopBinPath = os.path.join(self.getFinalInstallPath(), "bin")
    startDfsCmd = os.path.join(hadoopBinPath, "start-dfs.sh")
    cmd = self.getUserSwitchCmdStr() + "\"" + startDfsCmd + "\""
    return cmd


  def set_hdfs_started_flag(self):
    """ If we already started HDFS via another mechanism, set the flag
        that makes ensureHdfsStarted() think that it has already been
        started via that mechanism. """

    self.startedHdfs = True


  def ensureHdfsStarted(self):
    """ Ensures that the HDFS cluster that we just put together is started
        (starting it if necessary). This must be run in postinstall or
        later. """

    if self.startedHdfs or not self.mayStartDaemons():
      # already running, or not allowed to run this.
      return

    # If we're installing scribe too, make sure that we start it first
    # because we want to be able to capture the log output from Hadoop
    # in the central scribe logs.
    scribe_installer = toolinstall.getToolByName("scribe")
    if scribe_installer != None:
      scribe_installer.ensureScribeStarted()

    output.printlnVerbose("Starting HDFS")

    try:
      shell.sh(self.get_start_hdfs_cmd())
    except shell.CommandError:
      raise InstallError("Can't start HDFS")

    self.startedHdfs = True


  def ensureMapRedStarted(self):
    """ Ensures that the MapReduce cluster is started, starting it if
        necessary. Also starts HDFS at this time if need be. This must be
        run in postinstall or later. """

    if self.startedMapRed or not self.mayStartDaemons():
      # already running, or not allowed to run this.
      return

    self.ensureHdfsStarted()

    output.printlnVerbose("Starting MapReduce")
    hadoopBinPath = os.path.join(self.getFinalInstallPath(), "bin")
    startMrCmd = os.path.join(hadoopBinPath, "start-mapred.sh")
    cmd = self.getUserSwitchCmdStr() + "\"" + startMrCmd  + "\""

    try:
      shell.sh(cmd)
    except shell.CommandError:
      raise InstallError("Can't start Hadoop MapReduce")

    self.startedMapRed = True


  def get_hadoop_cmdline(self):
    """ Returns the path to bin/hadoop """

    hadoopBinPath = os.path.join(self.getFinalInstallPath(), "bin")
    hadoopCmd = os.path.join(hadoopBinPath, "hadoop")
    return self.getUserSwitchCmdStr() + "\"" + hadoopCmd + "\" "


  def hadoopCmd(self, args):
    """ Run a hadoop command with "bin/hadoop args" as the hadoop user.
        You are responsible for ensuring that the appropriate services
        are started by calling ensure*Started() yourself, first.
        Returns all lines returned by the hadoop command. """

    hadoop_cmdline = self.get_hadoop_cmdline()
    cmd = hadoop_cmdline + args

    try:
      lines = shell.shLines(cmd)
    except shell.CommandError:
      raise InstallError("Error executing command: " + cmd)

    return lines


  def waitForSafemode(self):
    """ Return when safemode is exited, or throw InstallError if we
        can't do this within our timeout interval. You are responsible
        for starting HDFS first yourself. """

    startTime = time.time()

    while time.time() < startTime + MAX_SAFE_MODE_WAIT_TIME:
      # determine whether we're in or out of safe mode.
      lines = self.hadoopCmd("dfsadmin -safemode get")
      if len(lines) > 0:
        statusLine = lines[0].strip()
        if statusLine == "Safe mode is OFF":
          return

      # wait a few seconds before polling again.
      time.sleep(3)

    raise InstallError("Timeout waiting for safemode to exit")


  def precheckUsername(self):
    """ Check that the configured hadoop username exists on this machine.
        Also, if we are in unattend mode, you can only configure Hadoop
        as a different username iff you are currently root. """

    output.printlnVerbose("Checking for Hadoop username")

    self.curUsername = self.getCurrUser()

    self.hadoopUser = self.properties.getProperty(HADOOP_USER_NAME_KEY, None)
    if self.hadoopUser == None:
      if self.curUsername == "root":
        # don't run hadoop as root; run it as "hadoop"
        self.hadoopUser = HADOOP_USER_NAME_DEFAULT
      else:
        # non-root install: run hadoop as yourself.
        self.hadoopUser = self.curUsername
    elif self.curUsername != "root" and self.hadoopUser != self.curUsername \
        and self.isUnattexnded():
      raise InstallError( \
"""In unattended mode, you cannot specify another username to run hadoop
if you are not installing as root. Please re-run the installer as root,
or specify your own username with --hadoop-user""")


    # Now make sure the hadoop username exists.
    try:
      shell.shLines("getent passwd \"" + self.hadoopUser + "\"")
    except shell.CommandError:
      output.printlnError("You must create the '%(username)s' username, " % \
         { "username" : self.hadoopUser } \
         + "or specify")
      output.printlnError("an alternate username with --hadoop-user")
      raise InstallError("Could not find username: " + self.hadoopUser)

    output.printlnVerbose("Found username: " + self.hadoopUser)


  def precheckLzoLibs(self):
    """ Check that liblzo2.so.2 is installed in one of /lib, /usr/lib,
        /usr/local/lib, anything on $LD_LIBRARY_PATH. It is okay if
        this is not here, but we disable support for native LZO
        compression in Hadoop if it is missing. (And display a warning
        to the user)"""

    testDirs = [ "/lib", "/usr/lib", "/usr/local/lib" ]
    ldLibraryPath = os.getenv("LD_LIBRARY_PATH", "")
    if len(ldLibraryPath) > 0:
      ldLibraryParts = ldLibraryPath.split(":")
      testDirs.extend(ldLibraryPaths)

    for dir in testDirs:
      libPath = os.path.join(dir, "liblzo2.so.2")
      if os.path.exists(libPath):
        output.printlnVerbose("Found LZO compression lib at " + libPath)
        self.libLzoFound = True
        return

  def canUseLzo(self):
    """ Return True if precheckLzoLibs detected the correct LZO libraries """
    nativeAllowed = self.properties.getBoolean(ALLOW_NATIVE_COMPRESSION_KEY, \
        ALLOW_NATIVE_COMPRESSION_DEFAULT)

    # return self.libLzoFound  and nativeAllowed
    # TODO(aaron): Due to GPL licensing issues, LZO compression is disabled
    # until an alternate library provider can be found.
    return False


  def precheckBzipLibs(self):
    """ Check that libbz2.so.1 is installed in one of /lib, /usr/lib,
        /usr/local/lib, anything on $LD_LIBRARY_PATH. It is okay if
        this is not here, but we disable support for native LZO
        compression in Hadoop if it is missing. (And display a warning
        to the user)"""

    testDirs = [ "/lib", "/usr/lib", "/usr/local/lib" ]
    ldLibraryPath = os.getenv("LD_LIBRARY_PATH", "")
    if len(ldLibraryPath) > 0:
      ldLibraryParts = ldLibraryPath.split(":")
      testDirs.extend(ldLibraryPaths)

    for dir in testDirs:
      libPath = os.path.join(dir, "libbz2.so.1")
      if os.path.exists(libPath):
        output.printlnVerbose("Found bzip2 compression lib at " + libPath)
        self.libBzipFound = True
        return

  def canUseBzip(self):
    """ Return True if precheckBzipLibs detected the correct bzip libraries """
    # TODO(aaron): Watch HADOOP-4918; it seems as though bzip2 does not
    # work with sequence files. Think hard before we use this.
    return self.libBzipFound


  def getJavaHome(self):
    """ Return the location of JAVA_HOME (retrieved from global prereq) """
    return toolinstall.getToolByName("GlobalPrereq").getJavaHome()


  def getHadoopInstallPrefix(self):
    """ Return the installation prefix for Hadoop, underneath the
        distribution-wide installation prefix. """

    return os.path.join( \
        toolinstall.getToolByName("GlobalPrereq").getAppsPrefix(), \
        HADOOP_INSTALL_SUBDIR)

  def getConfDir(self):
    """ return the dir where the hadoop config files go. """
    return os.path.join(self.getHadoopInstallPrefix(), "conf")


  def configMasterAddress(self):
    """ Sets the masterHost property of this object to point to the
        master server address for Hadoop, querying the user if necessary """

    # TODO(aaron): 0.2 - We currently conflate the master address here with
    # the address used for the secondary namenode. we should have a better
    # system which actually differentiates between the two, and puts scribe,
    # and the 2NN on a separate machine. This is an 0.2+ feature. (CH-85)

    defHostName = self.properties.getProperty(HADOOP_MASTER_ADDR_KEY)
    if defHostName == None:
      # look up the fqdn of this machine; we assume it's the master
      try:
        hostNameLines = shell.shLines("hostname --fqdn")
        if len(hostNameLines) == 0:
          defHostName = None
        else:
          defHostName = hostNameLines[0].strip()
      except shell.CommandError:
        defHostName = None

    if self.isUnattended():
      if defHostName == None:
        output.printlnError("No master address found, nor could it be inferred")
        output.printlnError("Please specify one with --hadoop-master")
        raise InstallError("Master address not set")
      else:
        maybeMasterHost = defHostName
    else:
      set = False
      while not set:
        maybeMasterHost = prompt.getString( \
            "Input the master host DNS address", defHostName, True)
        if dnsregex.isIpAddress(maybeMasterHost):
          output.printlnError("The master address must be a DNS name, " \
              + "not an IP address")
        elif not dnsregex.isDnsName(maybeMasterHost):
          output.printlnError("This does not appear to be a DNS address")
        else:
          set = True # this address seems legit.


    # make sure that this is an FQDN, not an IP address
    # Check again here regardless of what codepath we took to get here
    if dnsregex.isIpAddress(maybeMasterHost):
      output.printlnError("The master address must be a DNS name, " \
          + "not an IP address")
      raise InstallError("Master address format error")
    if not dnsregex.isDnsName(maybeMasterHost):
      raise InstallError("Master address does not appear to be a DNS name")

    # we're good.
    self.masterHost = maybeMasterHost


  def getMasterHost(self):
    return self.masterHost


  def getNumSlaves(self):
    return toolinstall.getToolByName("GlobalPrereq").getNumSlaves()


  def getTempSlavesFileName(self):
    return toolinstall.getToolByName("GlobalPrereq").getTempSlavesFileName()


  def configHadoopLogDir(self):
    """ Configure where Hadoop writes its log files """

    # grab the path from --hadoop-log-dir, default is ${HADOOP_HOME}/logs
    self.hadoop_log_dir = self.properties.getProperty(HADOOP_LOG_DIR_KEY, HADOOP_LOG_DIR_DEFAULT);
    if not self.isUnattended():
      logging.info("""
Hadoop stores log files containing diagnostic information for troubleshooting.
By default, these are stored in a subdirectory of the Hadoop installation. You
can override this setting here. Any relative paths will be joined to the Hadoop
install directory.
""")
      self.hadoop_log_dir = prompt.getString("Where should Hadoop log files be stored?", \
          self.hadoop_log_dir, True)

    logging.debug("Storing Hadoop logs in " + self.hadoop_log_dir)


  def configHadoopSite(self):
    """ The hadoop-site.xml file is the place where all the magic happens.
        If the user has already provided us with a hadoop-site file, then
        do nothing. Otherwise, we need to ask the user questions about what
        should go in this file. Bail out if none is provided and we're not
        interactive. """

    numSlaves = self.getNumSlaves()
    prefix = self.getHadoopInstallPrefix()

    userHadoopSiteFile = self.properties.getProperty(HADOOP_SITE_FILE_KEY)
    if self.isUnattended() and userHadoopSiteFile == None:
      output.printlnError("Unattended installation requires a " \
          + "hadoop-site.xml file specification")
      output.printlnError("Please restart installation with --hadoop-site")
      raise InstallError("No hadoop site file specified")
    elif userHadoopSiteFile != None:
      userHadoopSiteFile = os.path.join(self.properties.getProperty(BASE_DIR_KEY),
          userHadoopSiteFile)
      if not os.path.exists(userHadoopSiteFile):
        raise InstallError("Could not find hadoop site file: " \
            + userHadoopSiteFile)

    # autoconfigure locations of dfs.hosts and dfs.hosts.exclude files if
    # the user has passed these in as command-line arguments.
    cmdlineDfsHosts = self.properties.getProperty(MAKE_DFS_HOSTS_KEY)
    if cmdlineDfsHosts != None:
      # This will be relative to the hadoop config path, if it's not an
      # absolute path on its own.
      cmdlineDfsHosts = os.path.join(self.getConfDir(), cmdlineDfsHosts)
      self.hadoopSiteDict[DFS_HOSTS_FILE] = cmdlineDfsHosts

    cmdlineDfsExcludes = self.properties.getProperty(MAKE_DFS_EXCLUDES_KEY)
    if cmdlineDfsExcludes != None:
      # This will be relative to the hadoop config path, if it's not an
      # absolute path on its own.
      cmdlineDfsExcludes = os.path.join(self.getConfDir(), cmdlineDfsExcludes)
      self.hadoopSiteDict[DFS_EXCLUDE_FILE] = cmdlineDfsExcludes



    if not self.isUnattended() and userHadoopSiteFile == None:
      # time to actually query the user about these things.
      self.configuredHadoopSiteOnline = True

      output.printlnInfo("\nMaster server addresses:")

      daemonAddrsOk = False
      localHostAddrRegex = re.compile("localhost\:")
      legalHostPortRegex = dnsregex.getDnsNameAndPortRegex()

      while not daemonAddrsOk:
        defaultJobTracker = self.getMasterHost() + ":" + str(DEFAULT_JT_PORT)
        jobTrackerName = \
            prompt.getString("Enter the hostname:port for the JobTracker", \
            defaultJobTracker, True)
        self.hadoopSiteDict[MAPRED_JOB_TRACKER] = jobTrackerName
        self.properties.setProperty(JOB_TRACKER_KEY, jobTrackerName)

        defaultNameNode = self.getMasterHost() + ":" + str(DEFAULT_NN_PORT)
        nameNodeName = \
            prompt.getString("Enter the hostname:port for the HDFS NameNode", \
            defaultNameNode, True)

        nameNodeUri = "hdfs://" + nameNodeName + "/"
        self.hadoopSiteDict[FS_DEFAULT_NAME] = nameNodeUri
        self.properties.setProperty(NAMENODE_KEY, nameNodeUri)

        # check to make sure they didn't put 'localhost' in either of these
        # and that they're legal host:port pairs
        jtMatch = localHostAddrRegex.match(jobTrackerName)
        jobTrackerIsLocalhost = jtMatch != None and jtMatch.start() == 0

        jtDnsMatch = legalHostPortRegex.match(jobTrackerName)
        jobTrackerIsDns = jtDnsMatch != None and jtDnsMatch.start() == 0 \
            and jtDnsMatch.end() == len(jobTrackerName)

        nnMatch = localHostAddrRegex.match(nameNodeName)
        nameNodeIsLocalhost = nnMatch != None and nnMatch.start() == 0

        nnDnsMatch = legalHostPortRegex.match(nameNodeName)
        nameNodeIsDns = nnDnsMatch != None and nnDnsMatch.start() == 0 \
            and nnDnsMatch.end() == len(nameNodeName)

        if jobTrackerIsLocalhost or nameNodeIsLocalhost:
          output.printlnInfo("""
WARNING: Master server address of 'localhost' will not be accessible by other
nodes.
""")
          daemonAddrsOk = prompt.getBoolean( \
              "Are you sure you want to use these addresses?", False, True)
        elif not jobTrackerIsDns or not nameNodeIsDns:
          output.printlnInfo("""
WARNING: You must enter a hostname:port pair for both of these entries.
Please enter a valid address for both the JobTracker and the NameNode.
""")
        else:
          # looks good; proceed.
          daemonAddrsOk = True


      output.printlnInfo("""
When HDFS files are deleted using the command-line tools, they are moved
to a Trash directory. The trash interval sets the interval in minutes
between automatic emptying of the trash directory. Setting this to 0
disables the Trash directory. (Important: The Trash directory does not
provide protection against programmatic deletion of files; only deletion
via the command-line tools.)""")
      self.hadoopSiteDict[FS_TRASH_INTERVAL] = \
          prompt.getInteger("Enter the trash interval", 0, None, \
          DEFAULT_TRASH_INTERVAL, True)

      output.printlnInfo("""
The Hadoop tmp directory (which will be created on each node) determines
where temporary outputs of Hadoop processes are stored. This can live in
/tmp, or some place where you have more control over where files are written.
Make sure there is plenty of space available here. If this install is to be used
in a multi-user setting, it is recommended that each user have his own
temporary directory; this can be achieved by including the string '${user.name}'
in the temp dir name (e.g., /tmp/hadoop-${user.name}).""")
      self.hadoopSiteDict[HADOOP_TMP_DIR] = \
          prompt.getString("Enter the Hadoop temp dir", HADOOP_TMP_DEFAULT, \
          True)

      # TODO(aaron): 0.2 - future versions should scan for devices on the
      # name node  and auto-recommend a comma-separated list
      output.printlnInfo("""
You must choose one or more paths on the master node where the HDFS
metadata will be written. (These will be created if they do not already
exist.) Data will be mirrored to all paths. These
should all be on separate physical devices. For reliability, you may want
to add a remote NFS-mounted directory to this list. Enter one or more
directories separated by commas.""")
      nameDirDefault = "/home/" + self.getHadoopUsername() + "/hdfs/name"
      self.hadoopSiteDict[DFS_NAME_DIR] = \
          prompt.getString("Enter the HDFS metadata dir(s)", \
          nameDirDefault, True)

      output.printlnInfo("""
You must choose one or more paths on each of the slave nodes where
the HDFS data will be written. Data is split evenly over these paths. (These
will be created if they do not exist.) These should all be on separate
physical devices. For good performance, never put any NFS-mounted directories
in this list. Enter one or more directories separated by commas.""")
      dataDirDefault = "/home/" + self.getHadoopUsername() + "/hdfs/data"
      self.hadoopSiteDict[DFS_DATA_DIR] = \
          prompt.getString("Enter the HDFS data dir(s)", \
          dataDirDefault, True)

      output.printlnInfo("""
You must choose one or more paths on each of the slave nodes where
job-specific data will be written during MapReduce job execution. Adding
multiple paths on separate physical devices will improve performance. (These
directories will be created if they do not exist.) Enter one or more
directories separated by commas. If creating multiple local directories
on separate drives, subpaths should include ${user.name} to allow
per-user local directories.""")
      mapredLocalDefault = os.path.join(self.hadoopSiteDict[HADOOP_TMP_DIR], \
          "mapred/local")

      self.hadoopSiteDict[MAPRED_LOCAL_DIR] = \
          prompt.getString("Enter the local job data dir(s)", \
          mapredLocalDefault, True)

      output.printlnInfo("""
You must choose one or more paths on the master node used by the HDFS
secondary namenode for metadata compaction. Performance will be improved if
these are on separate physical devices. Enter one or more directories
separated by commas.""")
      secondaryNamenodeDirDefault = "/home/" + self.getHadoopUsername() \
          + "/hdfs/secondary"
      self.hadoopSiteDict[NN2_CHECKPOINT_DIR] = prompt.getString( \
          "Enter the secondary NameNode's storage path(s)", \
          secondaryNamenodeDirDefault, True)

      # Grab some basic info about the slave machine setup. Between these
      # parameters and the number of slave nodes, we can infer reasonable
      # values for everything else in the system.

      output.printlnInfo("""
Please give me a bit more information about how your slave nodes are
configured:""")

      numSlaves = prompt.getInteger("Number of slave nodes", 1, None, \
          numSlaves, True)

      slaveRamMb = prompt.getInteger("Slave node RAM (in MB)", 1, None, \
          DEFAULT_RAM_GUESS, True)

      numSlaveCores = prompt.getInteger("Number of CPU cores", 1, None, \
          DEFAULT_CORES_GUESS, True)

      # Expert installation steps follow

      output.printlnInfo("""
The following settings are here for experts only. If you're unsure of what
to do, just accept the default values.""")

      defMapsPerNode = int(math.ceil(0.75 * numSlaveCores))
      self.hadoopSiteDict[MAPS_PER_NODE] = prompt.getInteger( \
          MAPS_PER_NODE, 1, None, defMapsPerNode, True)

      defReducesPerNode = int(math.ceil(0.5 * numSlaveCores))
      numReducesPerNode = prompt.getInteger( \
          REDUCES_PER_NODE, 1, None, defReducesPerNode, True)
      self.hadoopSiteDict[REDUCES_PER_NODE] = numReducesPerNode

      defReducesPerJob = int(math.ceil(0.95 * numSlaves * numReducesPerNode))
      defReducesPerJob = max(1, defReducesPerJob)
      self.hadoopSiteDict[REDUCES_PER_JOB] = prompt.getInteger( \
          REDUCES_PER_JOB, 0, None, defReducesPerJob, True)

      taskSlotsPerNode = self.hadoopSiteDict[MAPS_PER_NODE] \
          + self.hadoopSiteDict[REDUCES_PER_NODE]

      defRamPerTaskInMb = int(math.floor(0.95 * slaveRamMb / taskSlotsPerNode))
      defRamPerTaskInMb = max(MIN_CHILD_HEAP, defRamPerTaskInMb)

      ramPerTaskInMb = prompt.getInteger("Heap size per task child (in MB)",
          MIN_CHILD_HEAP, None, defRamPerTaskInMb, True)

      self.hadoopSiteDict[MAPRED_CHILD_JAVA_OPTS] = prompt.getString( \
          MAPRED_CHILD_JAVA_OPTS, "-Xmx" + str(ramPerTaskInMb) + "m")

      # The child.ulimit must be large enough for the task's heap, plus
      # Java's overhead. This is hard to pin down, but a 2x factor should
      # be totally safe and keep the system from completely freaking out
      ramPerTaskInKb = ramPerTaskInMb * 1024
      defTaskUlimit = ramPerTaskInKb * 2
      defTaskUlimit = max(defTaskUlimit, MIN_ULIMIT)
      self.hadoopSiteDict[MAPRED_CHILD_ULIMIT] = prompt.getInteger( \
          MAPRED_CHILD_ULIMIT, MIN_ULIMIT, None, defTaskUlimit, True)

      self.hadoopSiteDict[DFS_DATANODE_THREADS] = prompt.getInteger( \
          DFS_DATANODE_THREADS, 1, None, DEFAULT_DATANODE_THREADS, True)

      self.hadoopSiteDict[DFS_DATANODE_RESERVED] = prompt.getInteger( \
          DFS_DATANODE_RESERVED, 0, None, DEFAULT_RESERVED_DU, True)

      self.hadoopSiteDict[DFS_PERMISSIONS] = prompt.getBoolean( \
          "Enable DFS Permissions", True, True)

      self.hadoopSiteDict[DFS_REPLICATION] = prompt.getInteger( \
          DFS_REPLICATION, 1, DFS_MAX_REP, DEFAULT_REPLICATION, True)

      self.hadoopSiteDict[DFS_BLOCK_SIZE] = prompt.getInteger( \
          DFS_BLOCK_SIZE, 1, None, DEFAULT_BLOCK_SIZE, True)

      defaultMasterThreads = int(math.ceil(numSlaves / 2))
      defaultMasterThreads = max(MIN_DAEMON_THREADS, defaultMasterThreads)
      defaultMasterThreads = min(MAX_DAEMON_THREADS, defaultMasterThreads)

      self.hadoopSiteDict[DFS_NAMENODE_THREADS] = prompt.getInteger( \
          DFS_NAMENODE_THREADS, 1, None, defaultMasterThreads, True)

      self.hadoopSiteDict[JOBTRACKER_THREADS] = prompt.getInteger( \
          JOBTRACKER_THREADS, 1, None, defaultMasterThreads, True)

      # TODO(aaron): 0.2 - Handle IO_SORT_FACTOR, IO_SORT_MB and
      # and fs.inmemory.size.mb; recommend something for these as well?

      self.hadoopSiteDict[IO_FILEBUF_SIZE] = prompt.getInteger( \
          IO_FILEBUF_SIZE, 4096, None, DEFAULT_FILEBUF_SIZE, True)

      defaultParallelCopies = self.hadoopSiteDict[REDUCES_PER_JOB]
      defaultParallelCopies = max(MIN_PARALLEL_COPIES, defaultParallelCopies)
      defaultParallelCopies = min(MAX_PARALLEL_COPIES, defaultParallelCopies)
      self.hadoopSiteDict[MAPRED_PARALLEL_COPIES] = prompt.getInteger( \
          MAPRED_PARALLEL_COPIES, 1, None, defaultParallelCopies, True)

      defaultTaskTrackerThreads = int(math.ceil(1.2 * \
          self.hadoopSiteDict[MAPRED_PARALLEL_COPIES]))
      self.hadoopSiteDict[TASKTRACKER_HTTP_THREADS] = prompt.getInteger( \
          TASKTRACKER_HTTP_THREADS, 1, None, defaultTaskTrackerThreads, True)

      self.hadoopSiteDict[MAPRED_SPECULATIVE_MAP] = prompt.getBoolean( \
          MAPRED_SPECULATIVE_MAP, DEFAULT_SPECULATIVE_MAP, True)

      self.hadoopSiteDict[MAPRED_SPECULATIVE_REDUCE] = prompt.getBoolean( \
          MAPRED_SPECULATIVE_REDUCE, DEFAULT_SPECULATIVE_REDUCE, True)

      defaultSubmitReplication = int(math.floor(math.sqrt(numSlaves)))
      defaultSubmitReplication = \
          max(MIN_SUBMIT_REPLICATION, defaultSubmitReplication)
      defaultSubmitReplication = \
          min(MAX_SUBMIT_REPLICATION, defaultSubmitReplication)
      self.hadoopSiteDict[MAPRED_SUBMIT_REPLICATION] = prompt.getInteger( \
          MAPRED_SUBMIT_REPLICATION, 1, DFS_MAX_REP, \
          defaultSubmitReplication, True)

      self.hadoopSiteDict[MAPRED_SYSTEM_DIR] = prompt.getString( \
          MAPRED_SYSTEM_DIR, DEFAULT_MAPRED_SYS_DIR, True)

      defaultHostsFile = os.path.join(self.getConfDir(), "dfs.hosts")
      self.hadoopSiteDict[DFS_HOSTS_FILE] = prompt.getString( \
          DFS_HOSTS_FILE, defaultHostsFile, True)

      defaultExcludeFile = os.path.join(self.getConfDir(), "dfs.hosts.exclude")
      self.hadoopSiteDict[DFS_EXCLUDE_FILE] = prompt.getString( \
          DFS_EXCLUDE_FILE, defaultExcludeFile, True)


  def installMastersFile(self):
    """ Put the 'masters' file in hadoop conf dir """
    mastersFileName = os.path.join(self.getConfDir(), "masters")
    try:
      handle = open(mastersFileName, "w")
      handle.write(self.getMasterHost())
      handle.close()
    except IOError, ioe:
      raise InstallError("Could not write masters file: " + mastersFileName \
          + " (" + str(ioe) + ")")


  def writeSlavesList(self, handle):
    """ Write the list of slaves out to the given file handle """
    slavesInputFileName = self.getTempSlavesFileName()
    output.printlnDebug("Reading slaves input list from " + slavesInputFileName)

    try:
      inHandle = open(slavesInputFileName)
      slaves = inHandle.readlines()
      inHandle.close()
    except IOError, ioe:
      raise InstallError("Error reading the slaves file: " \
          + slavesInputFileName + " (" + str(ioe) + ")")

    for slave in slaves:
      handle.write(slave)


  def installSlavesFile(self):
    """ Put the slaves file in hadoop conf dir """
    slavesFileName = os.path.join(self.getConfDir(), "slaves")
    try:
      handle = open(slavesFileName, "w")
      self.writeSlavesList(handle)
      handle.close()
    except IOError, ioe:
      raise InstallError("Could not write slaves file: " + slavesFileName \
          + " (" + str(ioe) + ")")


  def installDfsHostsFile(self):
    """ write the dfs.hosts file (same contents as slaves) """
    try:
      dfsHostsFileName = self.getHadoopSiteProperty(DFS_HOSTS_FILE)
      if dfsHostsFileName != None and len(dfsHostsFileName) > 0:
        dfsHostsHandle = open(dfsHostsFileName, "w")
        self.writeSlavesList(dfsHostsHandle)
        dfsHostsHandle.close()
    except IOError, ioe:
      raise InstallError("Could not write DFS hosts file: " + dfsHostsFileName \
          + " (" + str(ioe) + ")")
    except KeyError:
      # we didn't do this part of the configuration in-tool, or the
      # user didn't provide a filename on the command line to use.
      pass


  def installDfsExcludesFile(self):
    """ Create an empty file that will be the user's excludes file. """
    try:
      excludeFileName = self.getHadoopSiteProperty(DFS_EXCLUDE_FILE)
      if excludeFileName != None and len(excludeFileName) > 0:
        handle = open(excludeFileName, "w")
        handle.close()
    except IOError, ioe:
      raise InstallError("Could not create DFS exclude file: " \
          + excludeFileName + " (" + str(ioe) + ")")
    except KeyError:
      # we didn't do this part of the configuration in-tool, or the
      # user didn't provide a filename on the command line to use.
      pass

  def writeHadoopSiteEpilogue(self, handle):
    """ Always write in the following keys; don't poll the user for this """

    handle.write("""
<property>
  <name>mapred.jobtracker.taskScheduler</name>
  <value>org.apache.hadoop.mapred.FairScheduler</value>
</property>
<property>
  <name>mapred.fairscheduler.allocation.file</name>
  <value>/usr/share/cloudera/hadoop/conf/fairscheduler.xml</value>
</property>

<property>
  <name>mapred.output.compression.type</name>
  <value>BLOCK</value>
  <description>If the job outputs are to compressed as SequenceFiles, how should
               they be compressed? Should be one of NONE, RECORD or BLOCK.
               Cloudera Hadoop switches this default to BLOCK for better
               performance.
  </description>
</property>
<property>
  <description>If users connect through a SOCKS proxy, we don't want their
   SocketFactory settings interfering with the socket factory associated
   with the actual daemons.</description>
  <name>hadoop.rpc.socket.factory.class.default</name>
  <value>org.apache.hadoop.net.StandardSocketFactory</value>
  <final>true</final>
</property>
<property>
  <name>hadoop.rpc.socket.factory.class.ClientProtocol</name>
  <value></value>
  <final>true</final>
</property>
<property>
  <name>hadoop.rpc.socket.factory.class.JobSubmissionProtocol</name>
  <value></value>
  <final>true</final>
</property>
""")

    # if LZO is available, turn this on by default.
    if self.canUseLzo():
      handle.write("""
<property>
  <name>mapred.map.output.compression.codec</name>
  <value>org.apache.hadoop.io.compress.LzoCodec</value>
  <description>If the map outputs are compressed, how should they be
               compressed? Cloudera Hadoop has detected native LZO compression
               libraries on your system and has selected these for better
               performance.
  </description>
</property>
<property>
  <name>mapred.compress.map.output</name>
  <value>true</value>
</property>
<property>
  <name>mapred.output.compression.codec</name>
  <value>org.apache.hadoop.io.compress.LzoCodec</value>
</property>
""")

    # Write out the whole list of compression codecs we support
    codecList = "org.apache.hadoop.io.compress.DefaultCodec," \
        + "org.apache.hadoop.io.compress.GzipCodec"
    if self.canUseLzo():
      codecList = codecList + ",org.apache.hadoop.io.compress.LzoCodec"
    # TODO(aaron): 0.2 - include bzip2 in official codec list after Hadoop .19
    handle.write("""
<property>
  <name>io.compression.codecs</name>
  <value>%(codecs)s</value>
  <description>A list of the compression codec classes that can be used
               for compression/decompression.</description>
</property>
""" % { "codecs" : codecList })

    # and write the really-last lines out
    hadoopconf.writePropertiesFooter(handle)


  def getHadoopSiteFilename(self):
    """ Return the filename where we installed hadoop-site.xml """
    return os.path.join(self.getConfDir(), "hadoop-site.xml")


  def installFairScheduler(self):
    """ Write out fairscheduler.xml """

    fair_scheduler_file = os.path.join(self.getConfDir(), "fairscheduler.xml")
    try:
      handle = open(fair_scheduler_file, "w")
      # File is currently empty -- just a placeholder.
      handle.write("""<?xml version="1.0"?>
<allocations>
</allocations>
""")
      handle.close()
    except IOError, ioe:
      raise InstallError("Could not write fairscheduler.xml file (" \
          + str(ioe) + ")")


  def installHadoopSiteFile(self):
    """ Write out the hadoop-site.xml file that the user configured. """

    destFileName = self.getHadoopSiteFilename()
    if self.configuredHadoopSiteOnline:
      # the user gave this to us param-by-param online. Write this out.

      try:
        handle = open(destFileName, "w")

        hadoopconf.writePropertiesHeader(handle)
        hadoopconf.writePropertiesBody(handle, self.hadoopSiteDict, \
            finalHadoopProperties)

        # Write prologue of "fixed parameters" that we always include.
        self.writeHadoopSiteEpilogue(handle)

        handle.close()
      except IOError, ioe:
        raise InstallError("Could not write hadoop-site.xml file (" \
            + str(ioe) + ")")
    else:
      # The user provided us with a hadoop-site file. write that out.
      hadoopSiteFileName = self.properties.getProperty(HADOOP_SITE_FILE_KEY)
      if hadoopSiteFileName == None:
        # We shouldn't get here, but for paranoia's sake
        raise InstallError("Unexpected error: no hadoop-site.xml provided?")
      hadoopSiteFileName = os.path.join(self.properties.getProperty(BASE_DIR_KEY), \
          hadoopSiteFileName)
      shutil.copyfile(hadoopSiteFileName, destFileName)


  def installHadoopEnvFile(self):
    """ Hadoop installs a file in conf/hadoop-env.sh; we need to augment
        this with our own settings to initialize JAVA_HOME and JMX """
    # See https://wiki.cloudera.com/display/engineering/Hadoop+Configuration

    # We need to open the file for append and, at minimum,  add JAVA_HOME
    # Also enable JMX on all the daemons.
    # TODO(aaron): 0.2 -Eventually we'll want to overwrite the whole thing.

    destFileName = os.path.join(self.getConfDir(), "hadoop-env.sh")
    try:
      handle = open(destFileName, "a")
      handle.write("\n")
      handle.write("# Additional configuration properties written by\n")
      handle.write("# Cloudera Hadoop installer\n")
      handle.write("export JAVA_HOME=\"" + self.getJavaHome() + "\"\n")
      handle.write("export " \
          + "HADOOP_NAMENODE_OPTS=\"" \
          + "-Dcom.sun.management.jmxremote.port=1091 "\
          + "-Dcom.sun.management.jmxremote.authenticate=false "\
          + "-Dcom.sun.management.jmxremote.ssl=false " \
          + "$HADOOP_NAMENODE_OPTS\"\n")
      handle.write("export " \
          + "HADOOP_SECONDARYNAMENODE_OPTS=\"" \
          + "-Dcom.sun.management.jmxremote.port=1092 "\
          + "-Dcom.sun.management.jmxremote.authenticate=false "\
          + "-Dcom.sun.management.jmxremote.ssl=false " \
          + "$HADOOP_SECONDARYNAMENODE_OPTS\"\n")
      handle.write("export " \
          + "HADOOP_DATANODE_OPTS=\"" \
          + "-Dcom.sun.management.jmxremote.port=1093 "\
          + "-Dcom.sun.management.jmxremote.authenticate=false "\
          + "-Dcom.sun.management.jmxremote.ssl=false " \
          + "$HADOOP_DATANODE_OPTS\"\n")
      handle.write("export " \
          + "HADOOP_JOBTRACKER_OPTS=\"" \
          + "-Dcom.sun.management.jmxremote.port=1094 "\
          + "-Dcom.sun.management.jmxremote.authenticate=false "\
          + "-Dcom.sun.management.jmxremote.ssl=false " \
          + "$HADOOP_JOBTRACKER_OPTS\"\n")
      handle.write("export " \
          + "HADOOP_TASKTRACKER_OPTS=\"" \
          + "-Dcom.sun.management.jmxremote.port=1095 "\
          + "-Dcom.sun.management.jmxremote.authenticate=false "\
          + "-Dcom.sun.management.jmxremote.ssl=false " \
          + "$HADOOP_TASKTRACKER_OPTS\"\n")
      handle.write("export " \
          + "HADOOP_BALANCER_OPTS=\"" \
          + "-Dcom.sun.management.jmxremote.port=1096 "\
          + "-Dcom.sun.management.jmxremote.authenticate=false "\
          + "-Dcom.sun.management.jmxremote.ssl=false " \
          + "$HADOOP_BALANCER_OPTS\"\n")

      log_dir = os.path.join("${HADOOP_HOME}", self.hadoop_log_dir)
      handle.write("export HADOOP_LOG_DIR=" + log_dir + "\n")

      handle.close()
    except IOError, ioe:
      raise InstallError("Could not edit hadoop-env.sh (" + str(ioe) + ")")


  def createPaths(self):
    """ Create any paths needed by this installation (e.g., dfs.data.dir) """
    # Create hadoop.tmp.dir, dfs.data.dir, dfs.name.dir, mapred.local.dir
    # Hadoop itself will actually create at least dfs.data.dir, dfs.name.dir
    # if they are needed, so this isn't too critical if the user hasn't
    # specifically identified them

    hadoopUser = self.getHadoopUsername()

    def makeSinglePath(path):
      path = path.strip()

      try:
        # check first: if this contains another hadoop variable, don't
        # create it now.
        path.index("${")
        return # skip since it contains a variable.
      except ValueError:
        pass # couldn't find the substring - good.

      try:
        output.printlnDebug("Creating path: " + path)
        dirutils.mkdirRecursive(path)
      except OSError, ose:
        raise InstallError("Could not create directory: " + path + " (" \
            + str(ose) + ")")
      cmd = "chown " + hadoopUser + " \"" + path + "\""
      try:
        shell.sh(cmd)
      except shell.CommandError:
        output.printlnError("Warning: could not change " + path + " owner to " \
            + hadoopUser)

    def makeMultiPaths(paths):
      pathList = paths.split(",")
      for path in pathList:
        makeSinglePath(path)

    def makePathForProperty(prop):
      try:
        path = self.hadoopSiteDict[prop]
        makeSinglePath(path)
      except KeyError:
        pass # don't make this one; not a big deal.

    def makePathsForProperty(prop):
      try:
        paths = self.hadoopSiteDict[prop]
        makeMultiPaths(paths)
      except KeyError:
        pass # don't make this one; not a big deal.

    makePathForProperty(HADOOP_TMP_DIR)

    # namenode metadata path is only necessary on the master node.
    if self.isMaster():
      makePathsForProperty(DFS_NAME_DIR)

    # always create these paths on all machines in case the master
    # is also employed as a datanode. Because the user may have told
    # us to create the NN dir and not the DN dir, we create and chown
    # it in advance to prevent errors later on. If unused, it'll just
    # stay quietly empty.
    makePathsForProperty(DFS_DATA_DIR)
    makePathsForProperty(MAPRED_LOCAL_DIR)

    # Now make the log dir and chown it to the hadoop username.
    logDir = self.hadoop_log_dir
    logDir = os.path.join(self.getFinalInstallPath(), self.hadoop_log_dir)
    makeSinglePath(logDir)

  def get_ssh_warning(self):
    " return a warning msg regarding the lack of ssh keys for the hadoop user "

    hadoop_user = self.getHadoopUsername()

    return """Warning: No ssh key is available for the Hadoop user, %(user)s.
Before you start Hadoop services, you will need to create keys for this user
using ssh-keygen.""" % { "user" : hadoop_user }


  def precheckSshKeys(self):
    """ If the Hadoop account's ssh doesn't exist and we're in unattended
        mode, we should just fail immediately with a warning. This only
        applies to the master, who can create/distribute these keys."""

    # This method must be run after precheckUsername(), because it can call
    # get_ssh_warning(), which requires that the hadoop username be set up.

    # Initial value of this is set by user with --create-keys flag;
    # this default is assumed to be in place before calling configSshKeys()
    self.create_ssh_key = self.properties.getBoolean(CREATE_SSHKEYS_KEY, \
        CREATE_SSHKEYS_DEFAULT)

    if self.isMaster() and self.isUnattended() and not self.hasSshKey() \
        and not self.create_ssh_key:
      if self.mayStartDaemons():
        raise InstallError("""Error: No ssh key available for the Hadoop user.
Hadoop services will not be able to start. To create keys, run this installer
with --create-keys. Alternatively, disable daemon launch during the install
process with --no-start-daemons.""")
      else:
        # ssh keys are missing, but we're not starting daemons. Just warn.
        logging.error(self.get_ssh_warning())
        self.warn_need_ssh_keys = True


  def precheck(self):
    """ If anything must be verified before we even get going, check those
        constraints in this method """

    self.precheckUsername()
    self.precheckSshKeys()
    self.precheckLzoLibs()
    self.precheckBzipLibs()


  def hasSshKey(self):
    """ Return True if the Hadoop user account has an ssh key file present."""
    # Search for .ssh/id_rsa, id_dsa in hadoop user's account.

    hadoop_user = self.getHadoopUsername()
    userDir = os.path.expanduser("~" + hadoop_user)
    userSshDir = os.path.join(userDir, ".ssh")
    rsaKey = os.path.join(userSshDir, "id_rsa")
    dsaKey = os.path.join(userSshDir, "id_dsa")

    if os.path.exists(rsaKey):
      output.printlnVerbose("Found " + hadoop_user + " ssh key: " + rsaKey)
      return True
    elif os.path.exists(dsaKey):
      output.printlnVerbose("Found " + hadoop_user + " ssh key: " + dsaKey)
      return True
    else:
      output.printlnVerbose("Could not find ssh key for user " + hadoop_user)
      return False


  def configSshKeys(self):
    """ Determine if the Hadoop account's ssh key exists. If not, offer to
        create it if the user so desires. This method is only run in the
        master installer. """

    # If we're not root, we can only create keys for ourselves.
    hadoop_username = self.getHadoopUsername()
    cur_username = self.getCurrUser()
    allow_ssh_keygen = self.isRoot() or cur_username == hadoop_username

    # note: self.create_ssh_key was initialzied during precheck phase.

    if not self.hasSshKey() and not self.isUnattended() and allow_ssh_keygen \
        and not self.create_ssh_key:
      # interactive - prompt the user to create keys or not (since the key
      # is missing, and they didn't tell us on the command line to do this.
      output.printlnInfo( \
"""I could not find an ssh key for the user '%(hadoopuser)s' selected to run
the Hadoop daemons. This will cause problems starting Hadoop.""" % \
    { "hadoopuser" : hadoop_username })

      self.create_ssh_key = prompt.getBoolean( \
          "Should I create and distribute ssh keys now?", self.create_ssh_key)


  def configure(self):
    """ Run the configuration stage. This is responsible for
        setting up the config files and asking any questions
        of the user. The software is not installed yet """

    if self.isMaster():
      self.configSshKeys()

    self.configMasterAddress()
    self.configHadoopLogDir()
    self.configHadoopSite()


  def getFinalInstallPath(self):
    return os.path.join(self.getInstallBasePath(), HADOOP_INSTALL_SUBDIR)


  def shouldCreateSshKey(self):
    """ Return true if we should create missing ssh keys. This is based on the
        property CREATE_SSHKEYS_KEY (from --create-keys) and any interactive
        response. """

    return self.create_ssh_key


  def createSshKeys(self):
    " Assumes its being run on the master; actually create ~hadoop/.ssh/id_rsa "

    hadoop_user = self.getHadoopUsername()
    output.printlnVerbose("Generating id_rsa file for " + hadoop_user)

    # mkdir ~hadoop/.ssh and set it mode 0750
    sshKeyDir = os.path.join(os.path.expanduser("~" + hadoop_user), ".ssh")
    try:
      if not os.path.exists(sshKeyDir):
        dirutils.mkdirRecursive(sshKeyDir)
        # permissions must be 0750 or more strict. Just set them to 0700.
        shell.sh("chmod go-rwx \"" + sshKeyDir + "\"")
        shell.sh("chown " + hadoop_user + " \"" + sshKeyDir + "\"")
    except OSError, ose:
      raise InstallError("Could not create " + sshKeyDir + ": " + str(ose))
    except shell.CommandError:
      raise InstallError("Could not set owner for " + sshKeyDir)

    # create the key file id_rsa and id_rsa.pub (we'll rename this below)
    try:
      rsaFilename = os.path.join(sshKeyDir, "id_rsa")
      shell.sh("ssh-keygen -b 2048 -t rsa -f \"" + rsaFilename + "\" -N ''")
    except shell.CommandError:
      raise InstallError("Could not run ssh-keygen; cannot create ssh keys")

    # copy id_rsa.pub into local authorized_keys file
    try:
      pubFilename = rsaFilename + ".pub"
      pubKeyHandle = open(pubFilename, "r")
      # This will give us a single \n-terminated line for this pub key.
      pubKeyString = pubKeyHandle.read()
      pubKeyHandle.close()

      # If there is an id_rsa.pub file present, then the authorized_keys
      # file is silently ignored by sshd. So we should rename this file
      # to something that doesn't interfere with other keys.
      finalPubFilename = pubFilename + ".cloudera"
      os.rename(pubFilename, finalPubFilename)
    except IOError, ioe:
      raise InstallError("Could not read public key: " + str(ioe))
    except OSError, ose:
      raise InstallError("Could not rename public key: "+ str(ose))

    try:
      authKeysFilename = os.path.join(sshKeyDir, "authorized_keys")
      authKeysHandle = open(authKeysFilename, "a")
      authKeysHandle.write("\n")
      authKeysHandle.write("# Cloudera Hadoop installer: added autogen key:\n")
      authKeysHandle.write(pubKeyString)
      authKeysHandle.close()
    except IOError, ioe:
      raise InstallError("Could not authorize public key: " + str(ioe))

    # set the file permissions on the above files.
    try:
      shell.sh("chown " + hadoop_user + " \"" + rsaFilename + "\"")
      shell.sh("chown " + hadoop_user + " \"" + finalPubFilename + "\"")
      shell.sh("chown " + hadoop_user + " \"" + authKeysFilename + "\"")
      shell.sh("chmod 0600 \"" + rsaFilename + "\"")
    except shell.CommandError:
      raise InstallError("Could not set ssh key file permissions.")

    # set the name of the public key file to redistribute to slaves
    self.redist_pubkey_filename = finalPubFilename


  def installPublicKey(self):
    """
        This is running on a slave. The master may have uploaded an id_rsa.pub
        file; we append this in ~hadoop/.ssh/authorized_keys, creating any
        dirs/files as needed.
    """

    hadoop_user = self.getHadoopUsername()
    pubkey_filename = self.properties.getProperty(HADOOP_PUBKEY_KEY)

    if pubkey_filename == None:
      return # Nothing to do here.

    output.printlnVerbose("Writing public key into authorized_keys file")

    try:
      handle = open(pubkey_filename)
      public_key = handle.read() # this is a single \n-terminated line
      handle.close()
    except IOError, ioe:
      raise InstallError("Cannot read public key: " + str(ioe))

    userSshDir = os.path.join(os.path.expanduser("~" + hadoop_user), ".ssh")
    if not os.path.exists(userSshDir):
      # Create ~hadoop/.ssh/
      try:
        dirutils.mkdirRecursive(userSshDir)
      except OSError, ose:
        raise InstallError("Cannot create ssh directory: " + str(ose))

      try:
        # make sure the user owns the dir, and it's 0750 or better; use 0700.
        shell.sh("chown " + hadoop_user + " \"" + userSshDir + "\"")
        shell.sh("chmod go-rwx \"" + userSshDir + "\"")
      except shell.CommandError:
        raise InstallError("Could not set permissions for " + userSshDir)

    # append this to the authorized_keys file.
    authKeyFile = os.path.join(userSshDir, "authorized_keys")
    setAuthKeysPerms = not os.path.exists(authKeyFile)
    try:
      handle = open(authKeyFile, "a")
      handle.write("# Cloudera Hadoop installer added public key:\n")
      handle.write(public_key)
      handle.close()
    except IOError, ioe:
      raise InstallError("Could not write public key data: " + str(ioe))

    if setAuthKeysPerms:
      # We created the file. chmod and chown it.
      try:
        shell.sh("chown " + hadoop_user + " \"" + authKeyFile + "\"")
        shell.sh("chmod 0600 \"" + authKeyFile + "\"")
      except shell.CommandError:
        raise InstallError("Error setting permissions on " + authKeyFile)


  def installSshKeys(self):
    """
        If being run on the master, creates local ssh keys for the hadoop
        user. After this is over the remote mgr module will scp the
        id_rsa.pub file to all the slaves.

        If being run on a slave, reads the id_rsa.pub file and inserts its
        contents in the Hadoop user's authorized_keys file.
    """

    if self.isMaster():
      if not self.hasSshKey() and self.shouldCreateSshKey():
        # Actually create the key files.
        self.createSshKeys()
    else:
      self.installPublicKey()



  def installPackage(self):
    """ Install the Hadoop tarball itself. """

    hadoopPackageName = os.path.abspath(os.path.join(PACKAGE_PATH, \
        HADOOP_PACKAGE))
    if not os.path.exists(hadoopPackageName):
      raise InstallError("Missing hadoop installation package " \
          + hadoopPackageName)

    installPath = self.getInstallBasePath()
    dirutils.mkdirRecursive(installPath)

    cmd = "tar -zxf \"" + hadoopPackageName + "\"" \
        + " -C \"" + installPath + "\""

    try:
      shell.sh(cmd)
    except shell.CommandError, ce:
      raise InstallError("Error unpacking hadoop (tar returned error)")


  def install(self):
    """ Run the installation itself. """

    if self.mayStartDaemons():
      # kill any running daemons before we attempt to restart them
      # or install over top of them.
      self.kill_all_hadoop_daemons()

    self.installSshKeys()

    self.installPackage()

    # write the config files out.
    if self.isMaster():
      output.printlnDebug("Performing master-specific Hadoop setup")
      self.installMastersFile()
      self.installSlavesFile()
      self.installDfsHostsFile()
      self.installDfsExcludesFile()

    self.installHadoopSiteFile()
    self.installFairScheduler()
    self.installHadoopEnvFile()
    self.createPaths()


  def getHadoopBinDir(self):
    """ Return the path to the hadoop executables """
    return os.path.join(self.getFinalInstallPath(), "bin")


  def getHadoopExecCmd(self):
    """ Return the path to the executable to run hadoop """
    return os.path.join(self.getHadoopBinDir(), "hadoop")


  def doFormatHdfs(self):
    """ Format DFS if the user wants it done. Default is false,
        as the user must specifically enable this. """

    maybeFormatHdfs = self.properties.getBoolean(FORMAT_DFS_KEY, \
        FORMAT_DFS_DEFAULT)
    if self.isUnattended():
      formatHdfs = maybeFormatHdfs
    else:
      output.printlnInfo("""
Before your Hadoop cluster is usable, the distributed filesystem must be
formatted. If this is a new cluster, you should select "yes" to format HDFS
and prepare the cluster for use. If you are installing this distribution on
an existing Hadoop cluster, all existing HDFS data will be invalidated by
this process.""")
      formatHdfs = prompt.getBoolean("Format HDFS now?", maybeFormatHdfs, \
          False)


    # Hadoop itself will prompt iff there is already a directory there.
    # But since we have already sent the user a warning in interactive mode
    # (or the user selected --format-hdfs in unattend mode, and presumably
    # knows what he's doing), we just sidestep this prompt.
    echoPrefix = "echo Y | "
    sudoPrefix = self.getUserSwitchCmdStr()
    hadoopExec = self.getHadoopExecCmd()
    formatCmd = "\"" + hadoopExec + "\" namenode -format"
    if formatHdfs:
      output.printlnVerbose("Formatting HDFS instance...")
      cmd = echoPrefix + sudoPrefix + formatCmd
      try:
        shell.sh(cmd)
      except shell.CommandError, ce:
        output.printlnError("Could not format HDFS; Hadoop returned error")
        raise InstallError("Error formatting HDFS")
      logging.info("""Formatted HDFS. If you had existing data in the HDFS data directories,
you must clear and reinitialize those directories before using Hadoop.""")
    else:
      self.hdfsFormatMsg = \
"""HDFS was not formatted. If you have not done this before, you must format
HDFS before using Hadoop, by running the command:
%(cmd)s""" % { "cmd" : formatCmd }


  def postInstall(self):
    """ Run any post-installation activities. This occurs after
        all ToolInstall objects have run their install() operations. """

    if self.isMaster():
      self.doFormatHdfs()

    self.createInstallSymlink("hadoop")

    configDirSrc = os.path.join(self.getFinalInstallPath(), "conf")
    self.createEtcSymlink("hadoop", configDirSrc)


  def verify(self):
    """ Run post-installation verification tests, if configured """
    # TODO(aaron): Verify hadoop

    if self.isMaster() and self.mayStartDaemons():
      try:
        self.ensureHdfsStarted()
        self.ensureMapRedStarted()
        self.hadoopCmd("fs -ls /")
        self.verified = True
      except InstallError, ie:
        output.printlnError("Error starting Hadoop services: " + str(ie))
        output.printlnError("Cannot verify correct Hadoop installation")

      # TODO(aaron): Run a sample 'pi' job. Also, do a touchz, ls, rm


  def getRedeployArgs(self):
    argList = []
    hadoopMaster = self.getMasterHost()
    argList.append("--hadoop-master")
    argList.append(hadoopMaster)

    argList.append("--hadoop-user")
    argList.append(self.getHadoopUsername())

    argList.append(HADOOP_LOG_DIR_ARG)
    argList.append(self.hadoop_log_dir)

    return argList

  def printFinalInstructions(self):
    if self.hdfsFormatMsg != None:
      logging.info(self.hdfsFormatMsg)
    if self.warn_need_ssh_keys:
      logging.info(self.get_ssh_warning())


  def preserve_state(self, handle):
    pmap = {
      "configured_site_online" : self.configuredHadoopSiteOnline,
      "hadoop_site_dict"       : self.hadoopSiteDict,
      "lib_lzo_found"          : self.libLzoFound,
      "lib_bzip_found"         : self.libBzipFound,
      # TODO: These next two are transient state -- they should not be included in
      # what we memoize ,and we should determine the correct values on restart.
      "started_hdfs"           : self.startedHdfs,
      "started_mr"             : self.startedMapRed,
      "hadoop_user"            : self.hadoopUser,
      "cur_username"           : self.curUsername,
      "verified"               : self.verified,
      "hdfs_format_msg"        : self.hdfsFormatMsg,
      "hadoop_log_dir"         : self.hadoop_log_dir,
      "create_ssh_key"         : self.create_ssh_key,
      "redist_pubkey_filename" : self.redist_pubkey_filename,
      "warn_need_ssh_keys"     : self.warn_need_ssh_keys
    }

    pickle.dump(handle, pmap)


  def restore_state(self, handle, role_list, version):
    self.role_list = role_list
    pmap = pickle.load(handle)

    if version == "0.2.0":
      self.restore_0_2_0(pmap)
    else:
      raise InstallError("Cannot read state from file for version " + version)

  def restore_0_2_0(self, pmap):
    """ Read an 0.2.0 formatted pickle map """

    self.configuredHadoopSiteOnline = pmap["configured_site_online"]
    self.hadoopSiteDict             = pmap["hadoop_site_dict"]
    self.libLzoFound                = pmap["lib_lzo_found"]
    self.libBzipFound               = pmap["lib_bzip_found"]
    self.startedHdfs                = pmap["started_hdfs"]
    self.startedMapRed              = pmap["started_mr"]
    self.hadoopUser                 = pmap["hadoop_user"]
    self.curUsername                = pmap["cur_username"] # TODO(aaron) This needs validation.
    self.verified                   = pmap["verified"]
    self.hdfsFormatMsg              = pmap["hdfs_format_msg"]
    self.hadoop_log_dir             = pmap["hadoop_log_dir"]
    self.create_ssh_key             = pmap["create_ssh_key"]
    self.redist_pubkey_filename     = pmap["redist_pubkey_filename"]
    self.warn_need_ssh_keys         = pmap["warn_need_ssh_keys"]


