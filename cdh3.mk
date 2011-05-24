CDH_VERSION=3

# Hadoop 0.20.0-based hadoop package
HADOOP20_NAME=hadoop
HADOOP20_RELNOTES_NAME=Apache Hadoop
HADOOP20_PKG_NAME=hadoop-0.20
HADOOP20_BASE_VERSION=0.20.2
HADOOP20_TARBALL_DST=hadoop-$(HADOOP20_BASE_VERSION)-r916569.tar.gz
HADOOP20_TARBALL_SRC=$(HADOOP20_TARBALL_DST)
HADOOP20_SOURCE_MD5=1d6bd7ef87ae9a8f603d195a6f9fcfbd
HADOOP20_SITE=$(CLOUDERA_ARCHIVE)
HADOOP20_GIT_REPO=$(REPO_DIR)/cdh3/hadoop-0.20
HADOOP20_BASE_REF=cdh-base-$(HADOOP20_BASE_VERSION)
HADOOP20_BUILD_REF=HEAD
HADOOP20_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh3/hadoop-0.20-package
$(eval $(call PACKAGE,hadoop20,HADOOP20))

# ZooKeeper
ZOOKEEPER_NAME=zookeeper
ZOOKEEPER_RELNOTES_NAME=Apache Zookeeper
ZOOKEEPER_PKG_NAME=hadoop-zookeeper
ZOOKEEPER_BASE_VERSION=3.3.3
ZOOKEEPER_TARBALL_DST=zookeeper-$(ZOOKEEPER_BASE_VERSION).tar.gz
ZOOKEEPER_TARBALL_SRC=$(ZOOKEEPER_TARBALL_DST)
ZOOKEEPER_GIT_REPO=$(REPO_DIR)/cdh3/zookeeper
ZOOKEEPER_BASE_REF=cdh-base-$(ZOOKEEPER_BASE_VERSION)
ZOOKEEPER_BUILD_REF=cdh-$(ZOOKEEPER_BASE_VERSION)+12
ZOOKEEPER_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh3/zookeeper-package
ZOOKEEPER_SITE=$(CLOUDERA_ARCHIVE)
$(eval $(call PACKAGE,zookeeper,ZOOKEEPER))

# HBase
HBASE_NAME=hbase
HBASE_RELNOTES_NAME=Apache HBase
HBASE_PKG_NAME=hadoop-hbase
HBASE_BASE_VERSION=0.90.1
HBASE_TARBALL_DST=hbase-$(HBASE_BASE_VERSION).tar.gz
HBASE_TARBALL_SRC=$(HBASE_TARBALL_DST)
HBASE_GIT_REPO=$(REPO_DIR)/cdh3/hbase
HBASE_BASE_REF=cdh-base-$(HBASE_BASE_VERSION)
HBASE_BUILD_REF=cdh-$(HBASE_BASE_VERSION)+15
HBASE_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh3/hbase-package
HBASE_SITE=$(CLOUDERA_ARCHIVE)
$(eval $(call PACKAGE,hbase,HBASE))

# Pig
PIG_BASE_VERSION=0.8.1
PIG_NAME=pig
PIG_RELNOTES_NAME=Apache Pig
PIG_PKG_NAME=hadoop-pig
PIG_TARBALL_DST=pig-$(PIG_BASE_VERSION).tar.gz
PIG_TARBALL_SRC=$(PIG_TARBALL_DST)
PIG_GIT_REPO=$(REPO_DIR)/cdh3/pig
PIG_BASE_REF=cdh-base-$(PIG_BASE_VERSION)
PIG_BUILD_REF=cdh-$(PIG_BASE_VERSION)
PIG_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh3/pig-package
PIG_SITE=$(CLOUDERA_ARCHIVE)
$(eval $(call PACKAGE,pig,PIG))

# Hadoop Snappy
HADOOP_SNAPPY_NAME=hadoop-snappy
HADOOP_SNAPPY_RELNOTES_NAME=Hadoop Snappy
HADOOP_SNAPPY_PKG_NAME=hadoop-snappy
HADOOP_SNAPPY_BASE_VERSION=0.0.1
HADOOP_SNAPPY_TARBALL_DST=hadoop-snappy-$(HADOOP_SNAPPY_BASE_VERSION).tar.gz
HADOOP_SNAPPY_TARBALL_SRC=$(HADOOP_SNAPPY_TARBALL_DST)
HADOOP_SNAPPY_GIT_REPO=$(REPO_DIR)/cdh3/hadoop-snappy
HADOOP_SNAPPY_BASE_REF=cdh-base-$(HADOOP_SNAPPY_BASE_VERSION)
HADOOP_SNAPPY_BUILD_REF=cdh-$(HADOOP_SNAPPY_BASE_VERSION)
HADOOP_SNAPPY_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh3/hadoop-snappy-package
HADOOP_SNAPPY_SITE=http://golden.jenkins.sf.cloudera.com/job/hadoop-snappy-tarball/lastSuccessfulBuild/artifact/
$(eval $(call PACKAGE,hadoop-snappy,HADOOP_SNAPPY))

# Hive
HIVE_NAME=hive
HIVE_RELNOTES_NAME=Apache Hive
HIVE_RELEASE=2
HIVE_PKG_NAME=hadoop-hive
HIVE_BASE_VERSION=0.7.0
HIVE_TARBALL_DST=hive-$(HIVE_BASE_VERSION).tar.gz
HIVE_TARBALL_SRC=$(HIVE_TARBALL_DST)
HIVE_GIT_REPO=$(REPO_DIR)/cdh3/hive
HIVE_BASE_REF=cdh-base-$(HIVE_BASE_VERSION)
HIVE_BUILD_REF=cdh-$(HIVE_BASE_VERSION)+27
HIVE_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh3/hive-package
HIVE_SITE=$(CLOUDERA_ARCHIVE)
$(eval $(call PACKAGE,hive,HIVE))

HIVE_ORIG_SOURCE_DIR=$(HIVE_BUILD_DIR)/source
HIVE_SOURCE_DIR=$(HIVE_BUILD_DIR)/source/src

$(HIVE_TARGET_PREP):
	mkdir -p $($(PKG)_SOURCE_DIR)
	$(BASE_DIR)/tools/setup-package-build \
	  $($(PKG)_GIT_REPO) \
	  $($(PKG)_BASE_REF) \
	  $($(PKG)_BUILD_REF) \
	  $($(PKG)_DOWNLOAD_DST) \
	  $(HIVE_BUILD_DIR)/source \
	  $($(PKG)_FULL_VERSION)
	rsync -av $(HIVE_ORIG_SOURCE_DIR)/cloudera/ $(HIVE_SOURCE_DIR)/cloudera/
	touch $@

# Sqoop
SQOOP_NAME=sqoop
SQOOP_RELNOTES_NAME=Sqoop
SQOOP_PKG_NAME=sqoop
SQOOP_BASE_VERSION=1.2.0
SQOOP_TARBALL_DST=cdh-base-$(SQOOP_BASE_VERSION).tar.gz
SQOOP_TARBALL_SRC=$(SQOOP_TARBALL_DST)
SQOOP_GIT_REPO=$(REPO_DIR)/cdh3/sqoop
SQOOP_BASE_REF=cdh-base-$(SQOOP_BASE_VERSION)
SQOOP_BUILD_REF=cdh-$(SQOOP_BASE_VERSION)+24
SQOOP_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh3/sqoop-package
SQOOP_SITE=http://git.sf.cloudera.com/index.cgi/sqoop.git/snapshot/
$(eval $(call PACKAGE,sqoop,SQOOP))

# Oozie
OOZIE_NAME=oozie
OOZIE_RELNOTES_NAME=Apache Oozie
OOZIE_PKG_NAME=oozie
OOZIE_BASE_VERSION=2.3.0
OOZIE_TARBALL_DST=oozie-2.3.0.tar.gz
#OOZIE_TARBALL_SRC=oozie-2.3.0
OOZIE_TARBALL_SRC=ce428e55a36c3ee6a1f6d9a5abad9252b015ed85
OOZIE_GIT_REPO=$(REPO_DIR)/cdh3/oozie
OOZIE_BASE_REF=cdh-base-$(OOZIE_BASE_VERSION)
OOZIE_BUILD_REF=cdh-$(OOZIE_BASE_VERSION)+31
OOZIE_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh3/oozie-package
OOZIE_SITE=http://github.com/yahoo/oozie/tarball
$(eval $(call PACKAGE,oozie,OOZIE))

# Whirr
WHIRR_NAME=whirr
WHIRR_RELNOTES_NAME=Apache Whirr
WHIRR_PKG_NAME=whirr
WHIRR_BASE_VERSION=0.3.0
WHIRR_TARBALL_DST=whirr-$(WHIRR_BASE_VERSION)-incubating-src.tar.gz
WHIRR_TARBALL_SRC=$(WHIRR_TARBALL_DST)
WHIRR_GIT_REPO=$(BASE_DIR)/repos/cdh3/whirr
WHIRR_BASE_REF=cdh-base-$(WHIRR_BASE_VERSION)
WHIRR_BUILD_REF=cdh-$(WHIRR_BASE_VERSION)+5
WHIRR_PACKAGE_GIT_REPO=$(BASE_DIR)/repos/cdh3/whirr-package
WHIRR_SITE=$(CLOUDERA_ARCHIVE)
$(eval $(call PACKAGE,whirr,WHIRR))

$(WHIRR_TARGET_PREP):
	mkdir -p $($(PKG)_SOURCE_DIR)
	$(BASE_DIR)/tools/setup-package-build \
	  $($(PKG)_GIT_REPO) \
	  $($(PKG)_BASE_REF) \
	  $($(PKG)_BUILD_REF) \
	  $($(PKG)_DOWNLOAD_DST) \
	  $($(PKG)_SOURCE_DIR) \
	  $($(PKG)_FULL_VERSION)
	cp $(WHIRR_GIT_REPO)/cloudera/base.gitignore $(WHIRR_SOURCE_DIR)/.gitignore
	touch $@

# Flume
FLUME_NAME=flume
FLUME_RELNOTES_NAME=Flume
FLUME_PKG_NAME=flume
FLUME_BASE_VERSION=0.9.3
FLUME_TARBALL_DST=cdh-base-$(FLUME_BASE_VERSION).tar.gz
FLUME_TARBALL_SRC=$(FLUME_TARBALL_DST)
FLUME_GIT_REPO=$(REPO_DIR)/cdh3/flume
FLUME_BASE_REF=cdh-base-$(FLUME_BASE_VERSION)
FLUME_BUILD_REF=cdh-$(FLUME_BASE_VERSION)+15
FLUME_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh3/flume-package
FLUME_SITE=http://git.sf.cloudera.com/index.cgi/flume.git/snapshot/
$(eval $(call PACKAGE,flume,FLUME))
