#!/bin/bash -x
# (c) Copyright 2009 Cloudera, Inc.

set -e

function copy_logs_s3 {
  if [ -e $S3CMD ]; then
      $S3CMD put $S3_BUCKET:build/$BUILD_ID/deb_${CODENAME}_${DEB_HOST_ARCH}/user.log /var/log/user.log
  fi
}

if [ "x$INTERACTIVE" == "xFalse" ]; then
  trap "copy_logs_s3; hostname -f | grep -q ec2.internal && shutdown -h now;" INT TERM EXIT
  trap "hostname -f | grep -q ec2.internal && shutdown -h now;" INT TERM EXIT
fi

##SUBSTITUTE_VARS##
export AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY

############################## SETUP BUILD ENV ##############################

eval `dpkg-architecture` # set DEB_* variables

# Install things needed to build
export DEBIAN_FRONTEND=noninteractive

apt-get update

# Some basic tools we need:
#
#  devscripts - debian package building scripts
#  pbuilder - nice util for satisfying build deps
#  debconf-utils - for dch
#  liburi-perl - a dependency of one of the above that isn't resolved automatically
#  build-essential - compilers, etc
#  dctrl-tools - for dpkg-grepctrl

# Need to do this first so we can set the debconfs before other packages (e.g., postfix)
# get pulled in
apt-get -y install debconf-utils 

# Mark java license as accepted so that, if it's pulled in by some package, it won't
# block on user input to accept the sun license (ed: oracle license? haha)
echo 'sun-java6-bin   shared/accepted-sun-dlj-v1-1    boolean true
sun-java6-jdk   shared/accepted-sun-dlj-v1-1    boolean true
sun-java6-jre   shared/accepted-sun-dlj-v1-1    boolean true
sun-java6-jre   sun-java6-jre/stopthread        boolean true
sun-java6-jre   sun-java6-jre/jcepolicy note
sun-java6-bin   shared/present-sun-dlj-v1-1     note
sun-java6-jdk   shared/present-sun-dlj-v1-1     note
sun-java6-jre   shared/present-sun-dlj-v1-1     note
postfix  postfix/main_mailer_type  select  Local only
postfix  postfix/root_address  string 
postfix  postfix/rfc1035_violation  boolean  false
postfix  postfix/retry_upgrade_warning boolean
# Install postfix despite an unsupported kernel?
postfix  postfix/kernel_version_warning  boolean
postfix  postfix/mydomain_warning  boolean 
postfix  postfix/mynetworks  string  127.0.0.0/8 [::ffff:127.0.0.0]/104 [::1]/128
postfix  postfix/not_configured  error 
postfix  postfix/mailbox_limit string 0
postfix  postfix/relayhost string  
postfix  postfix/procmail  boolean false
postfix  postfix/bad_recipient_delimiter error 
postfix  postfix/protocols select  all
postfix  postfix/mailname  string  dontcare
postfix  postfix/tlsmgr_upgrade_warning  boolean 
postfix  postfix/recipient_delim  string +
postfix  postfix/main_mailer_type  select  Local only
postfix  postfix/destinations  string  localhost
postfix  postfix/chattr  boolean  false
' | debconf-set-selections

apt-get -y install devscripts pbuilder liburi-perl build-essential dctrl-tools 
apt-get -y install asciidoc xmlto

# Install s3cmd
pushd /tmp
  wget http://s3.amazonaws.com/ServEdge_pub/s3sync/s3sync.tar.gz
  tar xzvf s3sync.tar.gz
  export S3CMD=`pwd`/s3sync/s3cmd.rb
popd

############################## DOWNLOAD ##############################

for PACKAGE in $PACKAGES; do
 
  echo $PACKAGE

  mkdir /tmp/$BUILD_ID
  pushd /tmp/$BUILD_ID

  # fetch deb parts of manifest
  curl -s $MANIFEST_URL | grep ^$PACKAGE > manifest.txt

  # download all the files
  perl -n -a -e "
  if (/^$PACKAGE-deb/) {
    print \"Fetching \$F[1]...\\n\";
    system(\"/usr/bin/curl\", \"-s\", \"-o\", \$F[1], \$F[3]);
  }" manifest.txt

############################## BUILD ##############################

  # Unpack source package
  dpkg-source -x *dsc

  pushd `find . -maxdepth 1 -type d | grep -vx .`

  /usr/lib/pbuilder/pbuilder-satisfydepends

  if [ ! -z "$CODENAME" ]; then
    CODENAMETAG="~$CODENAME"
  fi
  VERSION=$(dpkg-parsechangelog | grep '^Version:' | awk '{print $2}')
  NEWVERSION=$VERSION$CODENAMETAG

  DEBEMAIL=info@cloudera.com \
    DEBFULLNAME="Cloudera Automatic Build System" \
    yes | dch --force-bad-version -v $NEWVERSION --distribution $CODENAME "EC2 Build ID $BUILD_ID"

  if [ -z "$DEBUILD_FLAG" ]; then
    DEBUILD_FLAG='-b'
  fi
  debuild -uc -us $DEBUILD_FLAG

  popd 

  pwd

  ############################## UPLOAD ##############################



  # we don't want to upload back the source change list
  rm *_source.changes

  FILES=$(grep-dctrl -n -s Files '' *changes | grep . | awk '{print $5}')

  for f in $FILES *changes ; do
      $S3CMD put $S3_BUCKET:build/$BUILD_ID/deb_${CODENAME}_${DEB_HOST_ARCH}/$(basename $f) $f
  done

  # Leave /tmp/$BUILD_ID
  popd

  rm -rf /tmp/$BUILD_ID

done

# Untrap, we're shutting down directly from here so the exit trap probably won't
# have time to do anything
if [ "x$INTERACTIVE" == "xFalse" ]; then
  trap - INT TERM EXIT
fi

copy_logs_s3

# If we're running on S3, shutdown the node
# (do the check so you can test elsewhere)
hostname -f | grep -q ec2.internal && shutdown -h now
