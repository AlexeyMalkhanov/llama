# (c) Copyright 2009 Cloudera, Inc.
#
# module: distrotester.installtests.installbase
#
# Abstract class containing functionality common to multihost and standalone tests.

import logging
import os
import socket
import tempfile
import unittest

import com.cloudera.distribution.sshall as sshall
from   com.cloudera.testutil.verbosetest import VerboseTestCase
import com.cloudera.tools.shell as shell

from   distrotester.constants import *
import distrotester.testproperties as testproperties
from   distrotester.functiontests.hadooptests import HadoopTest
from   distrotester.functiontests.hivetests import HiveTest
from   distrotester.functiontests.logmovertests import LogMoverTest
from   distrotester.functiontests.pigtests import PigTest
from   distrotester.functiontests.scribetests import ScribeTest
import distrotester.functiontests.secondarynamenodetests as secondarynamenodetests

class InstallBaseTest(VerboseTestCase):

  def __init__(self, methodName='runTest'):
    VerboseTestCase.__init__(self, methodName)
    self.curHadoopSite = None

    # Get our hostname and memoize it
    self.hostname = socket.getfqdn()


  def get_platform_setup(self):
    """ Get the PlatformSetup object used to initialize the node """

    # delaying this import til this thunk is used to avoid
    # circular dependency
    import distrotester.platforms as platforms

    properties = self.getProperties()
    platformName = properties.getProperty(TEST_PLATFORM_KEY)
    return platforms.setupForPlatform(platformName, properties)


  def enable_configuration(self, config_name, master_host):
    """
        Copy a Hadoop configuration from the distro tester into
        /etc/alternatives and enable it.
    """

    cur_config = self.getProperties().getProperty(CURRENT_CONFIG_KEY)

    if cur_config != config_name:
      src_path = os.path.join(HADOOP_CONFIG_SRCDIR, config_name)
      dest_path = HADOOP_CONFIG_DESTDIR
      self.doSshAll("cp -r " + src_path + " " + dest_path)

      full_dest_path = os.path.join(dest_path, config_name)
      hadoop_site_file = os.path.join(full_dest_path, "hadoop-site.xml")
      self.doSshAll("sed -i -e 's/MASTER_HOST/" + master_host+ "/' " + hadoop_site_file)
      self.doSshAll("alternatives --install /etc/hadoop/conf hadoop " + full_dest_path + " 50")
      self.doSshAll("alternatives --set hadoop " + full_dest_path)

      self.getProperties().setProperty(CURRENT_CONFIG_KEY, config_name)


  def getHadoopDir(self):
    return "/usr/lib/hadoop"

  def getHadoopCmd(self):
    return "hadoop"

  def getSlavesFile(self):
    """ Return the slaves file provided by the remote test manager """
    return self.getProperties().getProperty(SLAVES_FILE_KEY)

  def getSlavesList(self):
    slavesFile = self.getSlavesFile()
    try:
      handle = open(slavesFile)
      lines = handle.readlines()
      slavesList = []
      for line in lines:
        slavesList.append(line.strip())
      handle.close()
      return slavesList
    except IOError, ioe:
      logging.error("Error opening slaves file: " + str(slavesFile))
      logging.error(ioe)
      return []


  def getProperties(self):
    return testproperties.getProperties()

  def prepHadoopSite(self, inputHadoopSite):
    """ given an input hadoop-site.xml file we want to use, we must
        first replace the 'MASTER_HOST' string with the current
        hostname.
    """

    # Get a temporary filename to use as the hadoop-site.xml file.
    (oshandle, tmpFilename) = tempfile.mkstemp()
    self.curHadoopSite = tmpFilename
    try:
      handle = os.fdopen(oshandle, "w")
      handle.close()
    except OSError:
      # irrelevant
      pass
    except IOError:
      # irrelevant
      pass

    # put the hadoop site file through a sed script.
    script = 'sed -e "s/MASTER_HOST/' + self.hostname + '/" ' \
        + inputHadoopSite + " > " + self.curHadoopSite
    shell.sh(script)

    return self.curHadoopSite


  def stop_hadoop(self):
    self.doSshAll("service hadoop-namenode stop")
    self.doSshAll("service hadoop-secondarynamenode stop")
    self.doSshAll("service hadoop-jobtracker stop")
    self.doSshAll("service hadoop-datanode stop")
    self.doSshAll("service hadoop-tasktracker stop")


  def make_tmp_dir(self):
    """ Create the tmp dir under which all the Hadoop data lives """
    self.doSshAll("rm -rf /mnt/tmp")
    self.doSshAll("mkdir -p /mnt/tmp")
    self.doSshAll("chmod a+rwx /mnt/tmp")
    self.doSshAll("chmod o+t /mnt/tmp")


  def setUp(self):
    VerboseTestCase.setUp(self)
    self.make_tmp_dir()


  def tearDown(self):
    if self.curHadoopSite != None:
      # remove this temp file we created
      os.remove(self.curHadoopSite)

    # self.stop_hadoop()
    VerboseTestCase.tearDown(self)


  def doSshAll(self, cmd, slaves_only=False):
    " Execute a command on all hosts. "

    logging.debug("sshall command: " + cmd)

    allHosts = self.getSlavesList()
    if not slaves_only:
      # localhost too
      allHosts.append(self.hostname)

    results = sshall.sshMultiHosts("root", allHosts, cmd, \
        self.getProperties(), SSH_RETRIES, SSH_PARALLEL)
    for result in results:
      # each result is an sshall.SshResult obj
      if result.getStatus() != 0:
        logging.error("Got error status executing command on " \
            + result.getHost())
        logging.error("Output:")
        for line in result.getOutput():
          logging.error("  " + line.rstrip())


