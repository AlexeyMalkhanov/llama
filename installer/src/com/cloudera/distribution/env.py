# (c) Copyright 2008 Cloudera, Inc.
#
# module: com.cloudera.distribution.env
#
# Stores key/values that must be included in the user's environment
# before he can use the distribution. The various tools add entries to
# this list; it throws an InstallError if the same entry must be set
# to multiple conflicting values.

import os

from    com.cloudera.distribution.installerror import InstallError
import  com.cloudera.distribution.toolinstall as toolinstall
import  com.cloudera.tools.shell as shell
import  com.cloudera.util.output as output

envMap = {}

### public interface below this line ###
def addToEnvironment(key, val):
  """ Defines an environment variable "key" bound to "val" """
  global envMap
  try:
    curVal = envMap[key]
    if curVal != val:
      raise InstallError( \
"""The environment variable %(key)s requires multiple values:
%(val1)s
%(val2)s""" % { "key"  : key,
                "val1" : curVal,
                "val2" : val })
  except KeyError:
    # could not find the key; not set to anything. add the new value.
    envMap[key] = val


def printEnvironment():
  """ Prints the environment to the output """
  global envMap

  keys = envMap.keys()
  if len(keys) == 0:
    return # nothing to do

  keys.sort()
  output.printlnInfo( \
"""To use the tools in the Cloudera Hadoop distribution, you will need to
set the following environment variables. You should be able to paste this
directly into your .bashrc or /etc/profile files:""")
  for key in keys:
    output.printlnInfo("export " + key + "=" + envMap[key])

def writeEnvironmentScript():
  """ Writes out the environment variables we need to a script that users
      can source in.
  """

  global envMap

  keys = envMap.keys()
  if len(keys) == 0:
    return # nothing to do

  globalPrereq = toolinstall.getToolByName("GlobalPrereq")
  if None == globalPrereq:
    raise InstallError("No global prereq installer found?")

  keys.sort()
  envFilename = os.path.join(globalPrereq.getInstallPrefix(), "user_env")
  envFilename = os.path.abspath(envFilename)
  try:
    handle = open(envFilename, "w")
    handle.write("#!/bin/bash\n")
    for key in keys:
      handle.write("export " + key + "=" + envMap[key] + "\n")
    handle.close()
  except IOError, ioe:
    raise InstallError("Could not write " + envFilename + "\nreason: " \
        + str(ioe))

  # Now symlink this into the config dir
  configDir = os.path.abspath(globalPrereq.getConfigDir())
  configTarget = os.path.join(configDir, "user_env")
  cmd = "ln -s \"" + envFilename + "\" \"" + configTarget + "\""
  try:
    shell.sh(cmd)
  except shell.CommandError:
    raise InstallError("Could not create symlink: " + configTarget)


  output.printlnInfo("""
The required environment variable bindings have also been written to
%(filename)s
You may source this directly into your shell, or any other config scripts.""" \
      % { "filename" : envFilename })


