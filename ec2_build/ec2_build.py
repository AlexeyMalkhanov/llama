#!/usr/bin/env python2.5
# (c) Copyright 2009 Cloudera, Inc.
__usage = """
   --bucket | -b <bucket> bucket to dump sources and build products into
                          (default: ec2-build)

   --key | -k  <key>      SSH key to allow connection to build slave instances
                          (default: current user name)

   --groups | -g <group>  EC2 Access Groups, comma-separated, to use on build
                          slaves
                          (default: cloudera, <username>)

   --dir | -d <dir>       Build products directory where we find source debs and rpms
   --type <rpm|deb>       Only rebuild RPMs/debs
   --distro <distro>      Only build on given distro (eg centos5)
   --arch <arch>          Only build slaves of given arch (eg amd64)
   --dry-run | -n         Don't actually take any actions - just print out what
                          would normally happen

   --packages | -p <pkg>  Select package(s) to build may be listed multiple times
"""

# Sanity check:
#
# DEBIAN_DISTROS: lenny, hardy, intrepid, jaunty, etc
# DEBIAN_SUITES: stable, testing
# SUITE: $DEBIAN_DISTRO-$DEBIAN_SUITE, $DEBIAN_DISTRO-testing 
# CDH_RELEASE: cdh1, cdh2
# CODENAME: $DEBIAN_DISTRO-$CDH_RELEASE
# RELEASE: a build with version info hadoop-0.20_0.20.0+69+desktop.49-1cdh~intrepid-cdh2_i386

import boto
import datetime
import glob
import md5
from optparse import OptionParser
import os
import re
import sys
import time
import deb_util
from ec2_constants import AMIS, BUILD_INSTANCE_TYPES, DEFAULT_BUILD_MACHINES

# Expected location of build_[deb,rpm.sh]
SCRIPT_DIR = os.path.realpath(os.path.dirname(sys.argv[0]))

# Expected localtion of directories with sdebs and srpms
DEFAULT_BUILD_PRODUCTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output"))

# Default codename (needs to be bumped with every CDH release)
DEFAULT_CDH_RELEASE = 'cdh2'

# User running the script
try:
	USERNAME = os.getlogin()
except:
	USERNAME = "build"

POSSIBLE_PACKAGES = [ 'hadoop18', 'hadoop20', 'pig', 'hive' , 'zookeeper' ]
DEFAULT_PACKAGES = ['hadoop18', 'hadoop20']
# Build ID
BUILD_ID = "%s-%s" % (USERNAME, datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))

# Directory in S3_BUCKET to put files
FILECACHE_S3="file-cache"

# How long should manifests be valid for
EXPIRATION=60*60*24*7 # 7days

# Shell scripts to run to perform builds
BUILD_DEB=file(SCRIPT_DIR + "/build_deb.sh").read()
BUILD_RPM=file(SCRIPT_DIR + "/build_rpm.sh").read()

# These values are actually the entire shell script contents, which
# we need to pass through boto
BUILD_SCRIPTS = {
  'deb': BUILD_DEB,
  'rpm': BUILD_RPM,
  }

class Options:
  def __init__(self):
    # Bucket to store source RPMs/debs in
    self.S3_BUCKET = 'ec2-build'
    self.EC2_KEY_NAME = USERNAME
    self.EC2_GROUPS=['cloudera', USERNAME]
    self.BUILD_MACHINES = DEFAULT_BUILD_MACHINES
    self.CDH_RELEASE=DEFAULT_CDH_RELEASE
    self.BUILD_PRODUCTS_DIR=DEFAULT_BUILD_PRODUCTS_DIR
    self.DRY_RUN = False
    self.INTERACTIVE = False
    self.WAIT = False
    # Default to building hadoop
    self.PACKAGES = DEFAULT_PACKAGES
  pass

def parse_args():
  """ Parse command line arguments into globals. """

  ret_opts = Options()

  op = OptionParser(usage = __usage)
  op.add_option('-b', '--bucket')
  op.add_option('-k', '--key')
  op.add_option('-g', '--groups')
  op.add_option('-d', '--dir')
  op.add_option('-t', '--tag')
  op.add_option('--type', action='append')
  op.add_option('--distro', action='append')
  op.add_option('--arch', action='append')
  op.add_option('-n', '--dry-run', action='store_true')
  op.add_option('-p', '--packages', action='append', choices=POSSIBLE_PACKAGES)
  op.add_option("-i", '--interactive', action="store_true")
  op.add_option('-w', '--wait', action="store_true")

  opts, args = op.parse_args()

  if len(args):
    op.print_usage()
    raise Exception("Unhandled args: %s" % repr(args))

  if opts.groups:
    ret_opts.EC2_GROUPS = groups.split(',')

  if opts.arch:
    ret_opts.BUILD_MACHINES = [(type,distro,arch ) for (type, distro, arch) in ret_opts.BUILD_MACHINES if arch in opts.arch  ]

  if opts.distro:
    ret_opts.BUILD_MACHINES = [(type,distro,arch ) for (type, distro, arch) in ret_opts.BUILD_MACHINES if distro in opts.distro ]

  if opts.type:
    ret_opts.BUILD_MACHINES = [(type,distro,arch ) for (type, distro, arch) in ret_opts.BUILD_MACHINES if type in opts.type  ]

  ret_opts.DRY_RUN = opts.dry_run
  
  ret_opts.INTERACTIVE = opts.interactive

  ret_opts.WAIT = opts.wait

  if opts.bucket:
    ret_opts.S3_BUCKET = opts.bucket

  if opts.key:
    ret_opts.EC2_KEY_NAME = opts.key

  if opts.packages:
    ret_opts.PACKAGES = opts.packages

  if opts.dir:
    ret_opts.BUILD_PRODUCTS_DIR = opts.dir
  
  if opts.tag:
    ret_opts.CDH_RELEASE = opts.tag

  return ret_opts

def md5file(filename):
  """ Return the hex digest of a file without loading it all into memory. """
  fh = file(filename)
  digest = md5.new()
  while 1:
    buf = fh.read(4096)
    if buf == "":
      break
    digest.update(buf)
  fh.close()
  return digest.hexdigest()

def progressbar(bytes_done, total_bytes):
  """ Display a progress bar for boto file upload callback """
  print "Sent % 5d/%d KB" % (bytes_done/1024, total_bytes/1024),

  width = 60
  bar_len = (width * bytes_done / total_bytes)
  print "[" + ("=" * bar_len) + ">" + (" " * (width - bar_len - 1)) + "]",
  print "\r",
  sys.stdout.flush()

def satisfy_in_cache(bucket, path):
  """
  Ensure that the file at path 'path' is present in the file cache
  in bucket 'bucket'. Presence is determined by the md5sum of the
  file. If it is not present, uploads it.

  @param bucket an S3Bucket instance
  @param path a path on the local filesystem
  """
  checksum = md5file(path)

  print >>sys.stderr, "Trying to satisfy %s from cache..." % os.path.basename(path)
  s3_cache_path = "%s/%s" % (FILECACHE_S3, checksum)
  if not bucket.lookup(s3_cache_path):
    print >>sys.stderr, "not yet in cache - uploading..."
    k = bucket.new_key(s3_cache_path)
    k.set_contents_from_filename(path, cb=progressbar, num_cb=1000)
    print >>sys.stderr, "done"

  k = bucket.lookup(s3_cache_path)

  return (checksum, k.generate_url(EXPIRATION))

def upload_files_and_manifest(options, package_files):
  """
  Upload all of the required files as well as a manifest.txt file into
  the BUILD_ID dir on S3.

  @param package_files A dictionary keyed by the package to be build. Each key's value is dictionary keyed for deb|rpm that have lists of files needed to build the package
  """
  s3 = boto.connect_s3()
  bucket = s3.lookup(options.S3_BUCKET)
  if not bucket:
    error_string = "Unable to lookup bucket %s\n" % str(options.S3_BUCKET)
    error_string += "This is most likely due to not setting your"
    error_string += " AWS_SECRET_ACCESS_KEY correctly"
    raise Exception(error_string)


  build_dir = os.path.join("build", BUILD_ID)

  manifest_list = []

  for package in package_files:
    files = package_files[package]
    for package_format, paths in files.iteritems():
      for path in paths:
        dest = os.path.join(build_dir, os.path.basename(path))
        (checksum, url) = satisfy_in_cache(bucket, path)
        manifest_list.append(('-'.join([package, package_format]), os.path.basename(path), checksum, url))

  manifest = "\n".join(
    ["\t".join(el) for el in manifest_list])

  if not options.DRY_RUN:
    man_key = bucket.new_key('%s/manifest.txt' % build_dir)
    man_key.set_contents_from_string(
      manifest,
      headers={'Content-Type': 'text/plain'})
    return man_key.generate_url(EXPIRATION)
  else:
    return "<manifest not uploaded - dry run>"

def main():

  options = parse_args()

  # Figure out what packages need to built
  package_files = {}
  for package in options.PACKAGES:
    package_files[package] = {
      'deb': deb_util.find_source_deb_files(os.path.join(options.BUILD_PRODUCTS_DIR, package)),
      'rpm': glob.glob(os.path.join(options.BUILD_PRODUCTS_DIR, package, "*.src.rpm")),
    }

  manifest_url = upload_files_and_manifest(options, package_files)
  print manifest_url

  ec2 = boto.connect_ec2()

  instances = []
  for build_type, os_distro, arch in options.BUILD_MACHINES:
    ami = AMIS[(os_distro, arch)]
    image = ec2.get_image(ami)
    instance_type = BUILD_INSTANCE_TYPES[arch]
    start_script = BUILD_SCRIPTS[build_type]

    subs = {
      'build_id': BUILD_ID,
      'username': USERNAME,
      'os_distro': os_distro,
      'cdh_release': options.CDH_RELEASE,
      'interactive': str(options.INTERACTIVE),
      'manifest_url': manifest_url,
      'packages': ' '.join(options.PACKAGES),
      's3_bucket': options.S3_BUCKET,
      'aws_access_key_id': ec2.aws_access_key_id,
      'aws_secret_access_key': ec2.aws_secret_access_key,
      }

    subbed_script = start_script.replace(
      "##SUBSTITUTE_VARS##",
      """
      BUILD_ID='%(build_id)s'
      CDH_RELEASE='%(cdh_release)s'
      INTERACTIVE='%(interactive)s'
      BUILD_USER='%(username)s'
      CODENAME='%(os_distro)s-%(cdh_release)s'
      MANIFEST_URL='%(manifest_url)s'
      PACKAGES='%(packages)s'
      S3_BUCKET='%(s3_bucket)s'
      AWS_ACCESS_KEY_ID='%(aws_access_key_id)s'
      AWS_SECRET_ACCESS_KEY='%(aws_secret_access_key)s'
      """ % subs)

    print "Starting %s-%s build slave (%s)..." % (os_distro, arch, ami)
    if not options.DRY_RUN:
      reservation = image.run(
        key_name=options.EC2_KEY_NAME,
        security_groups=options.EC2_GROUPS,
        user_data=subbed_script,
        instance_type=instance_type)
      instances.append(reservation.instances[0])
    else:
      print "   [dry run: not starting]"

  print "Waiting for instances to boot..."
  for instance in instances:
    instance.update()
    while instance.state != 'running':
      print "   waiting on %s to start..." % instance.id
      time.sleep(5)
      instance.update()
    print "   Booted %s at %s" % (instance.id, instance.dns_name)

  print "All build slaves booted!"
  print
  print "To killall: "
  print "  ec2-terminate-instances %s" % (" ".join([i.id for i in instances]))
  print
  print "Expect results at s3://%s/build/%s/" % (options.S3_BUCKET, BUILD_ID)
  print "To update apt repo after build is finished:"
  print "  update_repo.sh %s %s" % (options.S3_BUCKET, BUILD_ID)

  if options.WAIT:
    print "Waiting for instances to terminate..."
    for instance in instances:
      instance.update()
      while instance.state != 'terminated':
        time.sleep(5)
        instance.update()
      print "   terminated %s" % (instance.id)

if __name__ == "__main__":
  main()
