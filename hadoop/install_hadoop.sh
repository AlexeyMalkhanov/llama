#!/bin/sh -x
# Copyright 2009 Cloudera, inc.

set -e

usage() {
  echo "
usage: $0 <options>
  Required not-so-options:
     --cloudera-source-dir=DIR   path to cloudera distribution files
     --build-dir=DIR             path to hive/build/dist
     --prefix=PREFIX             path to install into

  Optional options:
     --native-build-string       eg Linux-amd-64 (optional - no native installed if not set)
     --hadoop-config-location    eg /usr/bin/hadoop-config.sh or /etc/default/hadoop
     --java-home                 eg /usr/lib/jvm/java-6-sun/
     ... [ see source for more similar options ]
  "
  exit 1
}

OPTS=$(getopt \
  -n $0 \
  -o '' \
  -l 'cloudera-source-dir:' \
  -l 'prefix:' \
  -l 'build-dir:' \
  -l 'native-build-string:' \
  -l 'hadoop-config-location:' \
  -l 'doc-dir:' \
  -l 'java-home:' \
  -- "$@")

if [ $? != 0 ] ; then
    usage
fi

eval set -- "$OPTS"
while true ; do
    case "$1" in
        --cloudera-source-dir)
        CLOUDERA_SOURCE_DIR=$2 ; shift 2
        ;;
        --prefix)
        PREFIX=$2 ; shift 2
        ;;
        --build-dir)
        BUILD_DIR=$2 ; shift 2
        ;;
        --native-build-string)
        NATIVE_BUILD_STRING=$2 ; shift 2
        ;;
        --doc-dir)
        DOC_DIR=$2 ; shift 2
        ;;
        --hadoop-config-location)
        HADOOP_CONFIG_INSTALL_LOCATION=$2 ; shift 2
        ;;
        --java-home)
        JAVA_HOME=$2 ; shift 2
        ;;
        --)
        shift ; break
        ;;
        *)
        echo "Unknown option: $1"
        usage
        exit 1
        ;;
    esac
done

for var in CLOUDERA_SOURCE_DIR PREFIX BUILD_DIR ; do
  if [ -z "$(eval "echo \$$var")" ]; then
    echo Missing param: $var
    usage
  fi
done

LIB_DIR=${LIB_DIR:-$PREFIX/usr/lib/hadoop}
BIN_DIR=${BIN_DIR:-$PREFIX/usr/bin}
DOC_DIR=${DOC_DIR:-$PREFIX/usr/share/doc/hadoop}
EXAMPLE_DIR=${EXAMPLE_DIR:-$DOC_DIR/examples}
HADOOP_CONFIG_INSTALL_LOCATION=${HADOOP_CONFIG_INSTALL_LOCATION:-/etc/default/hadoop}
JAVA_HOME=${JAVA_HOME:-/usr/lib/jvm/java-6-sun/}

mkdir -p $LIB_DIR
(cd ${BUILD_DIR} && tar cf - .) | (cd $LIB_DIR && tar xf - )
# Take out things we've installed elsewhere

for x in docs lib/native c++ src conf ; do
  rm -rf $LIB_DIR/$x
done


# First, lets point all the bin scripts to the correct hadoop-config.sh file
for file in $LIB_DIR/bin/* ; do
    sed -i -e "s|^.*hadoop-config.sh.*\$|. $HADOOP_CONFIG_INSTALL_LOCATION|" $file
    sed -i -e 's|"$HADOOP_HOME"/bin/hadoop|/usr/bin/hadoop|' $file
done

# Mv bin elsewhere
mkdir -p $BIN_DIR
mv $LIB_DIR/bin/hadoop $BIN_DIR

# Fix some bad permissions in HOD
chmod 755 $LIB_DIR/contrib/hod/support/checklimits.sh
chmod 644 $LIB_DIR/contrib/hod/bin/VERSION

# Move examples to /usr/share
mkdir -p $EXAMPLE_DIR
mv $LIB_DIR/*examples*jar $EXAMPLE_DIR
cp -a $BUILD_DIR/src/examples/* $EXAMPLE_DIR

# Install docs
mkdir -p $DOC_DIR
cp -r ${BUILD_DIR}/docs/* $DOC_DIR

# Make the empty config
install -d -m 0755 $PREFIX/etc/hadoop/conf.empty
(cd ${BUILD_DIR}/conf && tar cf - .) | (cd $PREFIX/etc/hadoop/conf.empty && tar xf -)

# Make the pseudo-distributed config
install -d -m 0755 $PREFIX/etc/hadoop/conf.pseudo
(cd ${BUILD_DIR}/conf && tar -cf - .) | (cd $PREFIX/etc/hadoop/conf.pseudo && tar -xf -)
# Overwrite the hadoop-site.xml with our special pseudo-distributed one
cp ${CLOUDERA_SOURCE_DIR}/hadoop-site-pseudo.xml $PREFIX/etc/hadoop/conf.pseudo/hadoop-site.xml

mkdir -p `dirname $PREFIX$HADOOP_CONFIG_INSTALL_LOCATION`
mv $LIB_DIR/bin/hadoop-config.sh $PREFIX$HADOOP_CONFIG_INSTALL_LOCATION
sed -i -e "s|@JAVA_HOME@|$JAVA_HOME|" $PREFIX$HADOOP_CONFIG_INSTALL_LOCATION

# man page
mkdir -p $PREFIX/usr/man/man1
cp ${CLOUDERA_SOURCE_DIR}/hadoop.1.gz $PREFIX/usr/man/man1

############################################################
# ARCH DEPENDENT STUFF
############################################################

if [ ! -z "$NATIVE_BUILD_STRING" ]; then
  # Native compression libs
  mkdir -p $LIB_DIR/lib/native/
  cp -r ${BUILD_DIR}/lib/native/${NATIVE_BUILD_STRING} $LIB_DIR/lib/native/

  # Pipes
  mkdir -p $PREFIX/usr/lib $PREFIX/usr/include
  cp ${BUILD_DIR}/c++/${NATIVE_BUILD_STRING}/lib/libhadooppipes.a \
      ${BUILD_DIR}/c++/${NATIVE_BUILD_STRING}/lib/libhadooputils.a \
      $PREFIX/usr/lib
  cp -r ${BUILD_DIR}/c++/${NATIVE_BUILD_STRING}/include/hadoop $PREFIX/usr/include/

  # libhdfs
  cp ${BUILD_DIR}/c++/${NATIVE_BUILD_STRING}/lib/libhdfs.so.0.0.0 $PREFIX/usr/lib
  ln -s libhdfs.so.0.0.0 $PREFIX/usr/lib/libhdfs.so.0

  # libhdfs-dev - hadoop doesn't realy install these things in nice places :(
  mkdir -p $PREFIX/usr/share/doc/libhdfs0-dev/examples

  cp ${BUILD_DIR}/src/c++/libhdfs/hdfs.h $PREFIX/usr/include/
  cp ${BUILD_DIR}/src/c++/libhdfs/hdfs_*.c $PREFIX/usr/share/doc/libhdfs0-dev/examples

  #    This is somewhat unintuitive, but the -dev package has this symlink (see Debian Library Packaging Guide)
  ln -s libhdfs.so.0.0.0 $PREFIX/usr/lib/libhdfs.so
  sed -e "s|^libdir='.*'|libdir='/usr/lib'|" \
      ${BUILD_DIR}/c++/${NATIVE_BUILD_STRING}/lib/libhdfs.la > $PREFIX/usr/lib/libhdfs.la
fi
