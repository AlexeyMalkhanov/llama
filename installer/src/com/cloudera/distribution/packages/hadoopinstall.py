# (c) Copyright 2008 Cloudera, Inc.
#
# module: com.cloudera.distribution.packages.hadoopinstall
#
# Defines the ToolInstall instance that installs Hadoop

import math
import os
import re
import sys
import time

from   com.cloudera.distribution.constants import *
from   com.cloudera.distribution.installerror import InstallError
import com.cloudera.distribution.java as java
import com.cloudera.distribution.toolinstall as toolinstall
import com.cloudera.tools.shell as shell
import com.cloudera.util.output as output
import com.cloudera.util.prompt as prompt

def getJavaHomeFromUser(default):
  """ prompt the user for a valid value for JAVA_HOME """

  success = False
  while not success:
    javaHome = prompt.getString( \
        "Input the value for JAVA_HOME for Sun JRE 1.6", \
        default, False)
    if javaHome == None:
      output.printlnError("Error: Installing Hadoop requires " \
          + "a copy of Sun Java 1.6")
    else:
      success = True

  return javaHome


class HadoopInstall(toolinstall.ToolInstall):
  def __init__(self, properties):
    toolinstall.ToolInstall.__init__(self, "Hadoop", properties)

    self.addDependency("GlobalPrereq")

    self.configuredHadoopSiteOnline = False
    self.javaHome = None
    self.hadoopSiteDict = {}


  def getHadoopSiteProperty(self, propName):
    """ If the user configured hadoop-site in this tool, extract
        a property from the map the user created """
    return self.hadoopSiteDict[propName]

  def precheckJava(self):
    """ Check that Java 1.6 is installed """
    # We have to check for Sun Java 1.6
    javaHome = java.getJavaHome(self.properties)
    if self.isUnattended():
      if javaHome == None:
        output.printlnError( \
           """JAVA_HOME is not set, and the Java installation path was not set
  with --java-home. Please restart the installer with this configured.""")
        raise InstallError("Could not find compatible JAVA_HOME")
      else:
        output.printlnVerbose("Using JAVA_HOME of " + javaHome)
    else:
      # confirm that our value for JAVA_HOME is correct.
      # If the user didn't specify one, try to look for a reasonable value
      if javaHome == None:
        javaHomeGuess = java.guessJavaHome(self.properties)
      else:
        javaHomeGuess = javaHome

      javaHome = getJavaHomeFromUser(javaHomeGuess)

    # now that we have a value for JAVA_HOME, assert that we can find
    # Java there.
    while not java.canFindJDK(javaHome, self.properties):
      output.printlnError("An invalid JAVA_HOME was specified; " \
          + "this must point to Sun Java 1.6")

      if self.isUnattended():
        # Nothing to do but give up
        raise InstallError("Could not find compatible JAVA_HOME")
      else:
        # Ask the user for a better value for JAVA_HOME.
        javaHome = getJavaHomeFromUser(javaHome)

    self.javaHome = javaHome


  def getJavaHome(self):
    """ Return the value for JAVA_HOME we solicited and verified """
    return self.javaHome


  def precheckLzoLibs(self):
    """ Check that liblzo2.so.2 is installed in one of /lib, /usr/lib,
        /usr/local/lib, anything on $LD_LIBRARY_PATH. It is okay if
        this is not here, but we disable support for native LZO
        compression in Hadoop if it is missing. (And display a warning
        to the user)"""
    # TODO (aaron): This
    pass

  def canUseLzo(self):
    """ Return True if precheckLzoLibs detected the correct LZO libraries """
    # TODO: Destubify
    return False

  def precheckBzipLibs(self):
    """ Check that libbz2.so.1 is installed in one of /lib, /usr/lib,
        /usr/local/lib, anything on $LD_LIBRARY_PATH. It is okay if
        this is not here, but we disable support for native LZO
        compression in Hadoop if it is missing. (And display a warning
        to the user)"""
    # TODO (aaron): This (for 0.2 maybe)
    pass

  def canUseBzip(self):
    """ Return True if precheckBzipLibs detected the correct bzip libraries """
    # TODO: Destubify
    return False


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

    # TODO (aaron): We currently conflate the master address here with the
    # address used for the secondary namenode. we should have a better
    # system which actually differentiates between the two, and puts scribe,
    # and the 2NN on a separate machine.

    # regex for IP address: between 1 and 4 dot-separated numeric groups
    # which can be between 1 and 10 digits each (this is slightly more
    # liberal than required; but this captures dotted quads and dotted halves
    # and a single 32-bit value... and some other non-RFC-1035-compliant
    # values.

    ipAddrRegex = re.compile("[0-9]{1,10}(\.[0-9]{1,10}){0,3}")

    # regex for DNS addresses; this is slightly more liberal than RFC 1035
    dnsNameRegex = re.compile("[A-Za-z][0-9A-Za-z\._-]*")

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
        if ipAddrRegex.match(maybeMasterHost):
          output.printlnError("The master address must be a DNS name, " \
              + "not an IP address")
        elif not dnsNameRegex.match(maybeMasterHost):
          output.printlnError("This does not appear to be a DNS address")
        else:
          set = True # this address seems legit.


    # make sure that this is an FQDN, not an IP address
    # Check again here regardless of what codepath we took to get here
    if ipAddrRegex.match(maybeMasterHost):
      output.printlnError("The master address must be a DNS name, " \
          + "not an IP address")
      raise InstallError("Master address format error")
    if not dnsNameRegex.match(maybeMasterHost):
      output.printlnError("Master address does not appear to be a DNS name")
      raise InstallError("Master address format error")

    # we're good.
    self.masterHost = maybeMasterHost


  def getMasterHost(self):
    return self.masterHost

  def getNumSlaves(self):
    return toolinstall.getToolByName("GlobalPrereq").getNumSlaves()

  def getTempSlavesFileName(self):
    return toolinstall.getToolByName("GlobalPrereq").getTempSlavesFileName()


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
    elif userHadoopSiteFile != None and not os.path.exists(userHadoopSiteFile):
      output.printlnError("Could not find " + userHadoopSiteFile)
      raise InstallError("Could not find hadoop site file")

    if not self.isUnattended() and userHadoopSiteFile == None:
      # time to actually query the user about these things.
      self.configuredHadoopSiteOnline = True

      output.printlnInfo("\nMaster server addresses:")

      daemonAddrsOk = False
      while not daemonAddrsOk:
        defaultJobTracker = self.getMasterHost() + ":" + str(DEFAULT_JT_PORT)
        self.hadoopSiteDict[MAPRED_JOB_TRACKER] = \
            prompt.getString("Enter the hostname:port for the JobTracker", \
            defaultJobTracker, True)

        defaultNameNode = self.getMasterHost() + ":" + str(DEFAULT_NN_PORT)
        self.hadoopSiteDict[FS_DEFAULT_NAME] = "hdfs://" + \
            prompt.getString("Enter the hostname:port for the HDFS NameNode", \
            defaultNameNode, True) + "/"

        if self.hadoopSiteDict[MAPRED_JOB_TRACKER].startswith("localhost:") \
            or self.hadoopSiteDict[FS_DEFAULT_NAME].startswith( \
            "hdfs://localhost:"):
          output.printlnInfo("""
WARNING: Master server address of 'localhost' will not be accessible by other
nodes.
""")
          daemonAddrsOk = prompt.getBoolean( \
              "Are you sure you want to use these addresses?", False, True)
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
Make sure there is plenty of space available here.""")
      self.hadoopSiteDict[HADOOP_TMP_DIR] = \
          prompt.getString("Enter the Hadoop temp dir", HADOOP_TMP_DEFAULT, \
          True)

      # TODO (aaron): future versions of this should scan for devices on the
      # name node  and auto-recommend a comma-separated list
      output.printlnInfo("""
You must choose one or more paths on the master node where the HDFS
metadata will be written. (These will be created if they do not already
exist.) Data will be mirrored to all paths. These
should all be on separate physical devices. For reliability, you may want
to add a remote NFS-mounted directory to this list. Enter one or more
directories separated by commas.""")
      self.hadoopSiteDict[DFS_NAME_DIR] = \
          prompt.getString("Enter the HDFS metadata dir(s)", \
          HDFS_NAME_DIR_DEFAULT, True)

      output.printlnInfo("""
You must choose one or more paths on each of the slave nodes where
the HDFS data will be written. Data is split evenly over these paths. (These
will be created if they do not exist.) These should all be on separate
physical devices. For good performance, never put any NFS-mounted directories
in this list. Enter one or more directories separated by commas.""")
      self.hadoopSiteDict[DFS_DATA_DIR] = \
          prompt.getString("Enter the HDFS data dir(s)", \
          HDFS_DATA_DIR_DEFAULT, True)

      output.printlnInfo("""
You must choose one or more paths on each of the slave nodes where
job-specific data will be written during MapReduce job execution. Adding
multiple paths on separate physical devices will improve performance. (These
directories will be created if they do not exist.) Enter one or more
directories separated by commas.""")
      mapredLocalDefault = os.path.join(self.hadoopSiteDict[HADOOP_TMP_DIR], \
          "mapred/local")

      self.hadoopSiteDict[MAPRED_LOCAL_DIR] = \
          prompt.getString("Enter the local job data dir(s)", \
          mapredLocalDefault, True)

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

      defReducesPerJob = int(math.ceil(0.95 * numSlaves * numSlaveCores))
      defReducesPerJob = max(1, defReducesPerJob)
      self.hadoopSiteDict[REDUCES_PER_JOB] = prompt.getInteger( \
          REDUCES_PER_JOB, 0, None, defReducesPerJob, True)

      defMapsPerNode = int(math.ceil(0.75 * numSlaveCores))
      self.hadoopSiteDict[MAPS_PER_NODE] = prompt.getInteger( \
          MAPS_PER_NODE, 1, None, defMapsPerNode, True)

      defReducesPerNode = int(math.ceil(0.5 * numSlaveCores))
      self.hadoopSiteDict[REDUCES_PER_NODE] = prompt.getInteger( \
          REDUCES_PER_NODE, 1, None, defReducesPerNode, True)


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
      self.hadoopSiteDict[MAPRED_CHILD_ULIMIT] = prompt.getInteger( \
          MAPRED_CHILD_ULIMIT, 0, None, defTaskUlimit, True)

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

      # TODO (aaron): Handle IO_SORT_FACTOR, IO_SORT_MB and
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


      self.hadoopSiteDict[NN2_CHECKPOINT_DIR] = prompt.getString( \
          "Enter one or more comma-delimited directories for " \
          + "the secondary NameNode's data", HDFS_2NN_DIR_DEFAULT, True)

      self.hadoopSiteDict[MAPRED_SYSTEM_DIR] = prompt.getString( \
          MAPRED_SYSTEM_DIR, DEFAULT_MAPRED_SYS_DIR, True)

      defaultHostsFile = os.path.join(self.getConfDir(), "dfs.hosts")
      self.hadoopSiteDict[DFS_HOSTS_FILE] = prompt.getString( \
          DFS_HOSTS_FILE, defaultHostsFile, True)

      defaultExcludeFile = os.path.join(self.getConfDir(), "dfs.hosts.exclude")
      self.hadoopSiteDict[DFS_EXCLUDE_FILE] = prompt.getString( \
          DFS_EXCLUDE_FILE, defaultExcludeFile, True)

    # TODO: Figure out where the hadoop log dir should go to make things easiest
    # for alex. does this need to live anyplace in particular? can we allow the
    # user to customize this?


  def installMastersFile(self):
    """ Put the 'masters' file in hadoop conf dir """
    mastersFileName = os.path.join(self.getConfDir, "masters")
    try:
      handle = open(mastersFileName, "w")
      handle.write(self.getMasterHost())
      handle.close()
    except IOError, ioe:
      output.printlnError("Could not write masters file: " + mastersFileName)
      raise InstallError(ioe)


  def writeSlavesList(self, handle):
    """ Write the list of slaves out to the given file handle """
    slavesInputFileName = self.getTempSlavesFileName()

    try:
      inHandle = open(slavesInputFileName)
      slaves = inHandle.readLines()
      inHandle.close()
    except IOError, ioe:
      output.printlnError("Error reading the slaves file: " \
          + slavesInputFileName)
      raise InstallError(ioe)

    return slaves

  def installSlavesFile(self):
    """ Put the slaves file in hadoop conf dir """
    slavesFileName = os.path.join(self.getConfDir, "slaves")
    try:
      handle = open(slavesFileName, "w")
      self.writeSlavesList(handle)
      handle.close()
    except IOError, ioe:
      output.printlnError("Could not write slaves file: " + slavesFileName)
      raise InstallError(ioe)


  def installDfsHostsFile(self):
    """ write the dfs.hosts file (same contents as slaves) """
    try:
      dfsHostsFileName = self.getHadoopSiteProperty(DFS_HOSTS_FILE)
      if dfsHostsFileName != None and len(dfsHostsFileName) > 0:
        dfsHostsHandle = open(dfsHostsFileName, "w")
        self.writeSlavesList(dfsHostsHandle)
        dfsHostsHandle.close()
    except IOError, ioe:
      output.printlnError("Could not write DFS hosts file: " + dfsHostsFileName)
      raise InstallError(ioe)
    except KeyError:
      # we didn't do this part of the configuration in-tool.
      # If the user specified their own dfs.hosts file, install that.
      # TODO (aaron): Future versions of this tool should allow --dfs-hosts
      # So just let this slide for now.
      pass


  def installDfsExcludesFile(self):
    """ Create an empty file that will be the user's excludes file. """
    try:
      excludeFileName = self.getHadoopSiteProperty(DFS_EXCLUDE_FILE)
      if excludeFileName != None and len(excludeFileName) > 0:
        handle = open(excludeFileName, "w")
        handle.close()
    except IOError, ioe:
      output.printlnError("Could not create DFS exclude file: " \
          + excludeFileName)
      raise InstallError(ioe)
    except KeyError:
      # we didn't do this part of the configuration in-tool.
      # If the user specified their own dfs.hosts.exclude file, install that.
      # TODO (aaron): Future versions of this tool should allow --dfs-exclude
      # So just let this slide for now.
      pass

  def writeHadoopSiteEpilogue(self, handle):
    """ Always write in the following keys; don't poll the user for this """
    handle.write("""
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

    if self.canUseLzo():
      # TODO (aaron): include bzip2 in official codec list in 0.2
      handle.write("""
<property>
  <name>mapred.map.output.compression.codec</name>
  <value>org.apache.hadoop.io.compress.LzoCodec</value>
  <description>If the map outputs are compressed, how should they be
               compressed? Cloudera Hadoop has detected native LZO compression
               libraries on your system and has selected these for better
               perofrmance.
  </description>
</property>
<property>
  <name>mapred.compress.map.output</name>
  <value>true</value>
</property>
<property>
  <name>mapred.compress.map.output.codec</name>
  <value>org.apache.hadoop.io.compress.LzoCodec</value>
</property>
<property>
  <name>io.compression.codecs</name>
  <value>org.apache.hadoop.io.compress.DefaultCodec,org.apache.hadoop.io.compress.GzipCodec,org.apache.hadoop.io.compress.LzoCodec</value>
  <description>A list of the compression codec classes that can be used
               for compression/decompression.</description>
</property>
""")

    # This must be the last line in the file.
    handle.write("</configuration>\n")

  def installHadoopSiteFile(self):
    """ Write out the hadoop-site.xml file that the user configured. """

    def writeHadoopSiteKey(handle, key):
      try:
        finalHadoopProperties.index(key)
        # it's in the list of 'final' things. Mark is that way.
        finalStr = "\n  <final>true</final>"
      except ValueError:
        # not a final value, just a default.
        finalStr = ""

      handle.write("""<property>
  <name>%(name)s</name>
  <value>%(val)s</value>%(final)s
</property>
""" % {   "name"  : key,
          "val"   : self.getHadoopSiteProperty(key),
          "final" : finalStr })


    destFileName = os.path.join(self.getConfDir(), "hadoop-site.xml")
    if self.configuredHadoopSiteOnline:
      # the user gave this to us param-by-param online. Write this out.

      dateStr = time.asctime()
      try:
        handle = open(destFileName, "w")

        # Write the preamble
        handle.write("""<?xml version="1.0"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>

<!--
     Autogenerated by Cloudera Hadoop Installer on
     %(thedate)s

     You *may* edit this file. Put site-specific property overrides below.
-->
<configuration>
""" % { "thedate" : dateStr })

        # Write out everything the user configured for us.
        for key in self.hadoopSiteDict:
          writeHadoopSiteKey(handle, key)

        # Write prologue of "fixed parameters" that we always include.
        self.writeHadoopSiteEpilogue(self, handle)

        handle.close()
      except IOError, ioe:
        output.printlnError("Could not write hadoop-site.xml file")
        raise InstallError(ioe)
    else:
      # The user provided us with a hadoop-site file. write that out.
      hadoopSiteFileName = self.properties.getProperty(HADOOP_SITE_FILE_KEY)
      shutil.copyfile(hadoopSiteFileName, destFileName)

  def installHadoopEnvFile(self):
    """ Hadoop installs a file in conf/hadoop-env.sh; we need to augment
        this with our own settings to initialize JAVA_HOME and JMX """
    # See https://wiki.cloudera.com/display/engineering/Hadoop+Configuration

    # We need to open the file for append and, at minimum,  add JAVA_HOME
    # Also enable JMX on all the daemons.
    # TODO (aaron): Also allow overriding of the logging stuff?
    # TODO (aaron): Eventually we'll just want to overwrite the whole thing.

    destFileName = os.path.join(self.getConfDir(), "hadoop-env.sh")
    try:
      handle = open(destFileName, "a")
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

      handle.close()
    except IOError, ioe:
      output.printlnError("Could not edit hadoop-env.sh")
      raise InstallError(ioe)

  def createPaths(self):
    """ Create any paths needed by this installation (e.g., dfs.data.dir) """
    # TODO: Create hadoop.tmp.dir, dfs.data.dir, dfs.name.dir, mapred.local.dir
    # TODO: How does this work if we are given preassigned directories?
    # does hadoop create these in advance?

  def precheck(self):
    """ If anything must be verified before we even get going, check those
        constraints in this method """

    self.precheckJava()
    self.precheckLzoLibs()
    self.precheckBzipLibs()

  def configure(self):
    """ Run the configuration stage. This is responsible for
        setting up the config files and asking any questions
        of the user. The software is not installed yet """

    self.configMasterAddress()
    self.configHadoopSite()

  def install(self):
    """ Run the installation itself. """

    # Install the hadoop package itself
    hadoopPackageName = os.path.abspath(os.path.join(PACKAGE_PATH, \
        HADOOP_PACKAGE))
    if not os.path.exists(hadoopPackageName):
      output.printlnError("Error: Missing hadoop install package " + \
          hadoopPackageName)
      raise InstallError("Missing hadoop installation package")

    installPath = toolinstall.getToolByName("GlobalPrereq").getAppsPrefix(),

    if self.properties.getBoolean("output.verbose", False):
      verboseChar = "v"
    else:
      verboseChar = ""
    cmd = "tar -" + verboseChar + "zxf " + hadoopPackageName \
        + " -C " + installPath

    try:
      shell.sh(cmd)
    except CommandError, ce:
      output.printlnError("Could not install hadoop! tar returned error")
      raise InstallError("Error unpacking hadoop")

    # write the config files out.
    if self.properties.getProperty(HADOOP_PROFILE_KEY) == PROFILE_MASTER_VAL:
      self.installMastersFile()
      self.installSlavesFile()
      self.installDfsHostsFile()
      self.installDFsExcludesFile()

    self.installHadoopSiteFile()
    self.installHadoopEnvFile()
    self.createPaths()


  def postInstall(self):
    """ Run any post-installation activities. This occurs after
        all ToolInstall objects have run their install() operations. """
    # TODO postinstall hadoop
    # TODO: Format DFS if the user wants it done
    pass

  def verify(self):
    """ Run post-installation verification tests, if configured """
    # TODO: Verify hadoop
    # TODO: Start Hadoop daemons if the user wants it done
    # TODO: Run  'bin/hadoop fs -ls /' to make sure it works
    # (do a touchz, ls, rm)
    # TODO: Run a sample 'pi' job.
    pass


