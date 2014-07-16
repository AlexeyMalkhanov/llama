CDH_VERSION=5
CDH_CUSTOMER_PATCH=0
PREV_RELEASE_TAG=cdh5.0.0-release
export IVY_MIRROR_PROP=http://azov01.sf.cloudera.com:8081/artifactory/cloudera-mirrors/

CDH_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package
CDH_PACKAGE_VERSION=0.6.0

# Bigtop-utils
BIGTOP_UTILS_NAME=bigtop-utils
BIGTOP_UTILS_RELNOTES_NAME=Bigtop-utils
BIGTOP_UTILS_PKG_NAME=bigtop-utils
BIGTOP_UTILS_BASE_VERSION=0.7.0
BIGTOP_UTILS_PKG_VERSION=$(BIGTOP_UTILS_BASE_VERSION)+$(CDH_REL_STRING)+0
BIGTOP_UTILS_RELEASE_VERSION=1
BIGTOP_UTILS_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package
BIGTOP_UTILS_BASE_REF=cdh5-base-$(CDH_PACKAGE_VERSION)
BIGTOP_UTILS_BUILD_REF=HEAD
BIGTOP_UTILS_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package/bigtop-packages/src
$(eval $(call PACKAGE,bigtop-utils,BIGTOP_UTILS))

# Bigtop-jsvc
BIGTOP_JSVC_NAME=bigtop-jsvc
BIGTOP_JSVC_RELNOTES_NAME=Apache Commons Daemon (jsvc)
BIGTOP_JSVC_PKG_NAME=bigtop-jsvc
BIGTOP_JSVC_BASE_VERSION=1.0.10
#BIGTOP_JSVC_PKG_VERSION=$(BIGTOP_JSVC_BASE_VERSION)
BIGTOP_JSVC_RELEASE_VERSION=1
BIGTOP_JSVC_TARBALL_ONLY=true
BIGTOP_JSVC_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package
BIGTOP_JSVC_BASE_REF=cdh5-base-$(CDH_PACKAGE_VERSION)
BIGTOP_JSVC_TARBALL_SRC=commons-daemon-$(BIGTOP_JSVC_BASE_VERSION)-native-src.tar.gz
BIGTOP_JSVC_TARBALL_DST=commons-daemon-$(BIGTOP_JSVC_BASE_VERSION).tar.gz
BIGTOP_JSVC_SITE=$(CLOUDERA_ARCHIVE)
BIGTOP_JSVC_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package/bigtop-packages/src
$(eval $(call PACKAGE,bigtop-jsvc,BIGTOP_JSVC))

# Bigtop-tomcat
BIGTOP_TOMCAT_NAME=bigtop-tomcat
BIGTOP_TOMCAT_RELNOTES_NAME=Apache Tomcat
BIGTOP_TOMCAT_PKG_NAME=bigtop-tomcat
BIGTOP_TOMCAT_BASE_VERSION=6.0.37
BIGTOP_TOMCAT_PKG_VERSION=0.7.0+$(CDH_REL_STRING)+0
BIGTOP_TOMCAT_RELEASE_VERSION=1
BIGTOP_TOMCAT_TARBALL_ONLY=true
BIGTOP_TOMCAT_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package
BIGTOP_TOMCAT_BASE_REF=cdh5-base-$(CDH_PACKAGE_VERSION)
BIGTOP_TOMCAT_TARBALL_SRC=apache-tomcat-$(BIGTOP_TOMCAT_BASE_VERSION)-src.tar.gz
BIGTOP_TOMCAT_TARBALL_DST=apache-tomcat-$(BIGTOP_TOMCAT_BASE_VERSION).tar.gz
BIGTOP_TOMCAT_SITE=$(CLOUDERA_ARCHIVE)
BIGTOP_TOMCAT_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package/bigtop-packages/src
$(eval $(call PACKAGE,bigtop-tomcat,BIGTOP_TOMCAT))

# Hadoop
HADOOP_NAME=hadoop
HADOOP_RELNOTES_NAME=Apache Hadoop
HADOOP_PKG_NAME=hadoop
HADOOP_BASE_VERSION=2.3.0
HADOOP_RELEASE_VERSION=1
HADOOP_TARBALL_DST=hadoop-2.3.0-src.tar.gz
HADOOP_TARBALL_SRC=$(HADOOP_TARBALL_DST)
HADOOP_SITE=$(CLOUDERA_ARCHIVE)
HADOOP_GIT_REPO=$(REPO_DIR)/cdh5/hadoop
HADOOP_BASE_REF=cdh5-base-$(HADOOP_BASE_VERSION)
HADOOP_BUILD_REF=HEAD
HADOOP_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package/bigtop-packages/src
$(eval $(call PACKAGE,hadoop,HADOOP))

# ZooKeeper
ZOOKEEPER_NAME=zookeeper
ZOOKEEPER_RELNOTES_NAME=Apache Zookeeper
ZOOKEEPER_PKG_NAME=zookeeper
ZOOKEEPER_BASE_VERSION=3.4.5
ZOOKEEPER_RELEASE_VERSION=1
ZOOKEEPER_TARBALL_DST=zookeeper-$(ZOOKEEPER_BASE_VERSION).tar.gz
ZOOKEEPER_TARBALL_SRC=$(ZOOKEEPER_TARBALL_DST)
ZOOKEEPER_GIT_REPO=$(REPO_DIR)/cdh5/zookeeper
ZOOKEEPER_BASE_REF=cdh5-base-$(ZOOKEEPER_BASE_VERSION)
ZOOKEEPER_BUILD_REF=HEAD
ZOOKEEPER_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package/bigtop-packages/src
ZOOKEEPER_SITE=$(CLOUDERA_ARCHIVE)
$(eval $(call PACKAGE,zookeeper,ZOOKEEPER))

# HBase
HBASE_NAME=hbase
HBASE_RELNOTES_NAME=Apache HBase
HBASE_PKG_NAME=hbase
HBASE_BASE_VERSION=0.98.1
HBASE_RELEASE_VERSION=1
HBASE_TARBALL_DST=hbase-$(HBASE_BASE_VERSION)-src.tar.gz
HBASE_TARBALL_SRC=$(HBASE_TARBALL_DST)
HBASE_GIT_REPO=$(REPO_DIR)/cdh5/hbase
HBASE_BASE_REF=cdh5-base-$(HBASE_BASE_VERSION)
HBASE_BUILD_REF=HEAD
HBASE_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package/bigtop-packages/src
HBASE_SITE=$(CLOUDERA_ARCHIVE)
$(eval $(call PACKAGE,hbase,HBASE))

# Pig
PIG_NAME=pig
PIG_RELNOTES_NAME=Apache Pig
PIG_PKG_NAME=pig
PIG_BASE_VERSION=0.12.0
PIG_RELEASE_VERSION=1
PIG_TARBALL_DST=pig-$(PIG_BASE_VERSION).tar.gz
PIG_TARBALL_SRC=$(PIG_TARBALL_DST)
PIG_GIT_REPO=$(REPO_DIR)/cdh5/pig
PIG_BASE_REF=cdh5-base-$(PIG_BASE_VERSION)
PIG_BUILD_REF=HEAD
PIG_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package/bigtop-packages/src
PIG_SITE=$(CLOUDERA_ARCHIVE)
$(eval $(call PACKAGE,pig,PIG))

# Hive
HIVE_NAME=hive
HIVE_RELNOTES_NAME=Apache Hive
HIVE_PKG_NAME=hive
HIVE_BASE_VERSION=0.12.0
HIVE_RELEASE_VERSION=1
HIVE_TARBALL_DST=hive-$(HIVE_BASE_VERSION).tar.gz
HIVE_TARBALL_SRC=$(HIVE_TARBALL_DST)
HIVE_GIT_REPO=$(REPO_DIR)/cdh5/hive
HIVE_BASE_REF=cdh5-base-$(HIVE_BASE_VERSION)
HIVE_BUILD_REF=HEAD
HIVE_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package/bigtop-packages/src
HIVE_SITE=$(CLOUDERA_ARCHIVE)
HIVE_SRC_PREFIX=src/
$(eval $(call PACKAGE,hive,HIVE))

# # Sqoop
SQOOP_NAME=sqoop
SQOOP_RELNOTES_NAME=Sqoop
SQOOP_PKG_NAME=sqoop
SQOOP_BASE_VERSION=1.4.4
SQOOP_RELEASE_VERSION=1
SQOOP_TARBALL_DST=sqoop-$(SQOOP_BASE_VERSION).tar.gz
SQOOP_TARBALL_SRC=$(SQOOP_TARBALL_DST)
SQOOP_GIT_REPO=$(REPO_DIR)/cdh5/sqoop
SQOOP_BASE_REF=cdh5-base-$(SQOOP_BASE_VERSION)
SQOOP_BUILD_REF=HEAD
SQOOP_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package/bigtop-packages/src
SQOOP_SITE=$(CLOUDERA_ARCHIVE)
$(eval $(call PACKAGE,sqoop,SQOOP))

# # Sqoop 2
SQOOP2_NAME=sqoop2
SQOOP2_RELNOTES_NAME=Sqoop 2
SQOOP2_PKG_NAME=sqoop2
SQOOP2_BASE_VERSION=1.99.3
SQOOP2_RELEASE_VERSION=1
SQOOP2_TARBALL_DST=sqoop2-$(SQOOP2_BASE_VERSION).tar.gz
SQOOP2_TARBALL_SRC=sqoop-$(SQOOP2_BASE_VERSION).tar.gz
SQOOP2_GIT_REPO=$(REPO_DIR)/cdh5/sqoop2
SQOOP2_BASE_REF=cdh5-base-$(SQOOP2_BASE_VERSION)
SQOOP2_BUILD_REF=HEAD
SQOOP2_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package/bigtop-packages/src
SQOOP2_SITE=$(CLOUDERA_ARCHIVE)
$(eval $(call PACKAGE,sqoop2,SQOOP2))

# Oozie
OOZIE_NAME=oozie
OOZIE_RELNOTES_NAME=Apache Oozie
OOZIE_PKG_NAME=oozie
OOZIE_BASE_VERSION=4.0.0
OOZIE_RELEASE_VERSION=1
OOZIE_TARBALL_DST=oozie-$(OOZIE_BASE_VERSION).tar.gz
OOZIE_TARBALL_SRC=oozie-$(OOZIE_BASE_VERSION).tar.gz
OOZIE_GIT_REPO=$(REPO_DIR)/cdh5/oozie
OOZIE_BASE_REF=cdh5-base-$(OOZIE_BASE_VERSION)
OOZIE_BUILD_REF=HEAD
OOZIE_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package/bigtop-packages/src
OOZIE_SITE=$(CLOUDERA_ARCHIVE)
$(eval $(call PACKAGE,oozie,OOZIE))

# Whirr
WHIRR_NAME=whirr
WHIRR_RELNOTES_NAME=Apache Whirr
WHIRR_PKG_NAME=whirr
WHIRR_BASE_VERSION=0.9.0
WHIRR_RELEASE_VERSION=1
WHIRR_TARBALL_DST=whirr-$(WHIRR_BASE_VERSION)-pre-src.tar.gz
WHIRR_TARBALL_SRC=$(WHIRR_TARBALL_DST)
WHIRR_GIT_REPO=$(REPO_DIR)/cdh5/whirr
WHIRR_BASE_REF=cdh5-base-$(WHIRR_BASE_VERSION)
WHIRR_BUILD_REF=HEAD
WHIRR_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package/bigtop-packages/src
WHIRR_SITE=$(CLOUDERA_ARCHIVE)
$(eval $(call PACKAGE,whirr,WHIRR))

# $(WHIRR_TARGET_PREP):
# 	mkdir -p $($(PKG)_SOURCE_DIR)
# 	$(BASE_DIR)/tools/setup-package-build \
# 	  $($(PKG)_GIT_REPO) \
# 	  $($(PKG)_BASE_REF) \
# 	  $($(PKG)_BUILD_REF) \
# 	  $($(PKG)_DOWNLOAD_DST) \
# 	  $($(PKG)_SOURCE_DIR) \
# 	  $($(PKG)_FULL_VERSION)
# 	cp $(WHIRR_GIT_REPO)/cloudera/base.gitignore $(WHIRR_SOURCE_DIR)/.gitignore
# 	touch $@

# Flume NG
FLUME_NG_NAME=flume-ng
FLUME_NG_RELNOTES_NAME=Flume NG
FLUME_NG_PKG_NAME=flume-ng
FLUME_NG_BASE_VERSION=1.5.0
FLUME_NG_RELEASE_VERSION=1
FLUME_NG_GIT_REPO=$(REPO_DIR)/cdh5/flume-ng
FLUME_NG_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package/bigtop-packages/src
FLUME_NG_BASE_REF=cdh5-base-$(FLUME_NG_BASE_VERSION)
FLUME_NG_BUILD_REF=HEAD
FLUME_NG_TARBALL_DST=$(FLUME_NG_NAME)-$(FLUME_NG_BASE_VERSION).tar.gz
FLUME_NG_TARBALL_SRC=apache-flume-$(FLUME_NG_BASE_VERSION)-src.tar.gz
FLUME_NG_SITE=$(CLOUDERA_ARCHIVE)
$(eval $(call PACKAGE,flume-ng,FLUME_NG))

# Mahout
MAHOUT_NAME=mahout
MAHOUT_RELNOTES_NAME=Mahout
MAHOUT_PKG_NAME=mahout
MAHOUT_BASE_VERSION=0.9
MAHOUT_RELEASE_VERSION=1
MAHOUT_TARBALL_DST=mahout-distribution-$(MAHOUT_BASE_VERSION)-src.tar.gz
MAHOUT_TARBALL_SRC=$(MAHOUT_TARBALL_DST)
MAHOUT_GIT_REPO=$(REPO_DIR)/cdh5/mahout
MAHOUT_BASE_REF=cdh5-base-$(MAHOUT_BASE_VERSION)
MAHOUT_BUILD_REF=HEAD
MAHOUT_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package/bigtop-packages/src
MAHOUT_SITE=$(CLOUDERA_ARCHIVE)
$(eval $(call PACKAGE,mahout,MAHOUT))

# Hue
HUE_NAME=hue
HUE_RELNOTES_NAME=$(HUE_NAME)
HUE_PKG_NAME=$(HUE_NAME)
HUE_BASE_VERSION=3.6.0
HUE_RELEASE_VERSION=1
HUE_TARBALL_DST=$(HUE_NAME)-$(HUE_BASE_VERSION)-src.tar.gz
HUE_TARBALL_SRC=$(HUE_TARBALL_DST)
HUE_GIT_REPO=$(REPO_DIR)/cdh5/hue
HUE_BASE_REF=cdh5-base-$(HUE_BASE_VERSION)
HUE_BUILD_REF=HEAD
HUE_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package/bigtop-packages/src
HUE_SITE=$(CLOUDERA_ARCHIVE)
$(eval $(call PACKAGE,hue,HUE))

# DataFu 
DATAFU_NAME=datafu
DATAFU_RELNOTES_NAME=Collection of user-defined functions
DATAFU_PKG_NAME=pig-udf-datafu
DATAFU_BASE_VERSION=1.1.0
DATAFU_RELEASE_VERSION=1
DATAFU_TARBALL_DST=datafu-$(DATAFU_BASE_VERSION).tar.gz
DATAFU_TARBALL_SRC=$(DATAFU_TARBALL_DST)
DATAFU_GIT_REPO=$(REPO_DIR)/cdh5/datafu
DATAFU_BASE_REF=cdh5-base-$(DATAFU_BASE_VERSION)
DATAFU_BUILD_REF=HEAD
DATAFU_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package/bigtop-packages/src
DATAFU_SITE=$(CLOUDERA_ARCHIVE)
$(eval $(call PACKAGE,datafu,DATAFU))

# Solr
SOLR_NAME=solr
SOLR_RELNOTES_NAME=Search engine server
SOLR_PKG_NAME=solr
SOLR_BASE_VERSION=4.4.0
SOLR_RELEASE_VERSION=1
SOLR_TARBALL_DST=solr-$(SOLR_BASE_VERSION)-src.tgz
SOLR_TARBALL_SRC=$(SOLR_TARBALL_DST)
SOLR_GIT_REPO=$(REPO_DIR)/cdh5/solr
SOLR_BASE_REF=cdh5-base-$(SOLR_BASE_VERSION)
SOLR_BUILD_REF=HEAD
SOLR_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package/bigtop-packages/src
SOLR_SITE=$(CLOUDERA_ARCHIVE)
$(eval $(call PACKAGE,solr,SOLR))

# Search project 
SEARCH_NAME=search
SEARCH_RELNOTES_NAME=Cloudera Search Project
SEARCH_PKG_NAME=search
SEARCH_BASE_VERSION=1.0.0
#SEARCH_PKG_VERSION=$(SEARCH_BASE_VERSION)
SEARCH_RELEASE_VERSION=1
SEARCH_TARBALL_DST=search-$(SEARCH_BASE_VERSION).tar.gz
SEARCH_GIT_REPO=$(REPO_DIR)/cdh5/search
SEARCH_BUILD_REF=HEAD
SEARCH_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package/bigtop-packages/src
SEARCH_SITE=$(CLOUDERA_ARCHIVE)
$(eval $(call PACKAGE,search,SEARCH))

# Search project hbase-solr-indexer
HBASE_SOLR_NAME=hbase-solr
HBASE_SOLR_RELNOTES_NAME=NGData HBase indexer Project
HBASE_SOLR_PKG_NAME=hbase-solr
HBASE_SOLR_BASE_VERSION=1.5
#HBASE_SOLR_PKG_VERSION=$(HBASE_SOLR_BASE_VERSION)
HBASE_SOLR_RELEASE_VERSION=1
HBASE_SOLR_TARBALL_DST=hbase-solr-$(HBASE_SOLR_BASE_VERSION).tar.gz
HBASE_SOLR_GIT_REPO=$(REPO_DIR)/cdh5/hbase-solr
HBASE_SOLR_BUILD_REF=HEAD
HBASE_SOLR_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package/bigtop-packages/src
HBASE_SOLR_SITE=$(CLOUDERA_ARCHIVE)
$(eval $(call PACKAGE,hbase-solr,HBASE_SOLR))

# Kite
KITE_NAME=kite
KITE_RELNOTES_NAME=Kite Software Development Kit
KITE_PKG_NAME=kite
KITE_BASE_VERSION=0.10.0
KITE_RELEASE_VERSION=1
KITE_TARBALL_DST=kite-$(KITE_BASE_VERSION).tar.gz
KITE_TARBALL_SRC=release-$(KITE_BASE_VERSION).tar.gz
KITE_GIT_REPO=$(REPO_DIR)/cdh5/kite
KITE_BASE_REF=cdh5-base-$(KITE_BASE_VERSION)
KITE_BUILD_REF=HEAD
KITE_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package/bigtop-packages/src
KITE_SITE=$(CLOUDERA_ARCHIVE)
$(eval $(call PACKAGE,kite,KITE))

# Sentry 
SENTRY_NAME=sentry
SENTRY_RELNOTES_NAME=Cloudera authorization component
SENTRY_PKG_NAME=sentry
SENTRY_BASE_VERSION=1.3.0
SENTRY_RELEASE_VERSION=1
SENTRY_TARBALL_DST=sentry-$(SENTRY_BASE_VERSION).tar.gz
SENTRY_TARBALL_SRC=apache-sentry-$(SENTRY_BASE_VERSION)-incubating-src.tar.gz
SENTRY_GIT_REPO=$(REPO_DIR)/cdh5/sentry
SENTRY_BASE_REF=cdh5-base-$(SENTRY_BASE_VERSION)
SENTRY_BUILD_REF=HEAD
SENTRY_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package/bigtop-packages/src
SENTRY_SITE=$(CLOUDERA_ARCHIVE)
$(eval $(call PACKAGE,sentry,SENTRY))

# Impala
IMPALA_NAME=impala
IMPALA_RELNOTES_NAME=Cloudera Impala
IMPALA_PKG_NAME=impala
IMPALA_BASE_VERSION=1.5.0
IMPALA_PKG_VERSION=$(IMPALA_BASE_VERSION)+$(CDH_REL_STRING)+0
IMPALA_RELEASE_VERSION=1
IMPALA_BUILD_REF=HEAD
IMPALA_GIT_REPO=$(REPO_DIR)/cdh5/impala
IMPALA_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package/bigtop-packages/src/
IMPALA_TARBALL_DST=impala-cdh5-$(IMPALA_BASE_VERSION).tar.gz
$(eval $(call PACKAGE,impala,IMPALA))

# Llama
LLAMA_NAME=llama
LLAMA_RELNOTES_NAME=Cloudera Llama
LLAMA_PKG_NAME=llama
LLAMA_BASE_VERSION=1.0.0
#LLAMA_PKG_VERSION=$(LLAMA_BASE_VERSION)
LLAMA_RELEASE_VERSION=1
LLAMA_BUILD_REF=HEAD
LLAMA_GIT_REPO=$(REPO_DIR)/cdh5/llama
LLAMA_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package/bigtop-packages/src/
LLAMA_TARBALL_DST=llama-cdh5-$(LLAMA_BASE_VERSION).tar.gz
$(eval $(call PACKAGE,llama,LLAMA))

# Avro
AVRO_NAME=avro
AVRO_RELNOTES_NAME=Avro
AVRO_PKG_NAME=avro-libs
AVRO_BASE_VERSION=1.7.5
#AVRO_PKG_VERSION=$(AVRO_BASE_VERSION)
AVRO_RELEASE_VERSION=1
AVRO_BUILD_REF=HEAD
AVRO_BASE_REF=cdh5-base-$(AVRO_BASE_VERSION)
AVRO_GIT_REPO=$(REPO_DIR)/cdh5/avro
AVRO_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package/bigtop-packages/src
AVRO_TARBALL_DST=avro-$(AVRO_BASE_VERSION).tar.gz
AVRO_TARBALL_SRC=avro-src-$(AVRO_BASE_VERSION).tar.gz
AVRO_SITE=$(CLOUDERA_ARCHIVE)
$(eval $(call PACKAGE,avro,AVRO))

# Parquet
PARQUET_NAME=parquet
PARQUET_RELNOTES_NAME=Columnar storage format for Hadoop
PARQUET_PKG_NAME=parquet
PARQUET_BASE_VERSION=1.2.5
#PARQUET_PKG_VERSION=$(PARQUET_BASE_VERSION)
PARQUET_RELEASE_VERSION=1
PARQUET_TARBALL_DST=parquet-$(PARQUET_BASE_VERSION).tar.gz
PARQUET_TARBALL_SRC=parquet-$(PARQUET_BASE_VERSION).tar.gz
PARQUET_GIT_REPO=$(REPO_DIR)/cdh5/parquet
PARQUET_BASE_REF=cdh5-base-1.2.5
PARQUET_BUILD_REF=HEAD
PARQUET_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package/bigtop-packages/src
PARQUET_SITE=$(CLOUDERA_ARCHIVE)
$(eval $(call PACKAGE,parquet,PARQUET))

# Parquet Format
PARQUET_FORMAT_NAME=parquet-format
PARQUET_FORMAT_RELNOTES_NAME=Format definitions for parquet
PARQUET_FORMAT_PKG_NAME=parquet-format
PARQUET_FORMAT_BASE_VERSION=1.0.0
#PARQUET_FORMAT_PKG_VERSION=$(PARQUET_FORMAT_BASE_VERSION)
PARQUET_FORMAT_RELEASE_VERSION=1
PARQUET_FORMAT_TARBALL_SRC=parquet-format-$(PARQUET_FORMAT_BASE_VERSION).tar.gz
PARQUET_FORMAT_TARBALL_DST=$(PARQUET_FORMAT_TARBALL_SRC)
PARQUET_FORMAT_GIT_REPO=$(REPO_DIR)/cdh5/parquet-format
PARQUET_FORMAT_BASE_REF=cdh5-base-1.0.0
PARQUET_FORMAT_BUILD_REF=HEAD
PARQUET_FORMAT_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package/bigtop-packages/src
PARQUET_FORMAT_SITE=$(CLOUDERA_ARCHIVE)
$(eval $(call PACKAGE,parquet-format,PARQUET_FORMAT))

# Spark 
SPARK_NAME=spark
SPARK_RELNOTES_NAME=Lightning-Fast Cluster Computing
SPARK_PKG_NAME=spark-core
SPARK_BASE_VERSION=1.0.0
#SPARK_PKG_VERSION=$(SPARK_BASE_VERSION)
SPARK_RELEASE_VERSION=1
SPARK_TARBALL_SRC=spark-$(SPARK_BASE_VERSION).tgz
SPARK_TARBALL_DST=spark-$(SPARK_BASE_VERSION).tar.gz
SPARK_GIT_REPO=$(REPO_DIR)/cdh5/spark
SPARK_BASE_REF=cdh5-base-$(SPARK_BASE_VERSION)
SPARK_BUILD_REF=HEAD
SPARK_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package/bigtop-packages/src
SPARK_SITE=$(CLOUDERA_ARCHIVE)
$(eval $(call PACKAGE,spark,SPARK))

# CDH parcel packages
CDH_PARCEL_NAME=cdh-parcel
CDH_PARCEL_RELNOTES_NAME=CDH-Parcel
CDH_PARCEL_BASE_VERSION=5.2.0
CDH_PARCEL_PKG_NAME=cdh-parcel-$(CDH_PARCEL_BASE_VERSION)
CDH_PARCEL_RELEASE_VERSION=1
CDH_PARCEL_TARBALL_DST=$(CDH_PARCEL_NAME)-$(CDH_PARCEL_BASE_VERSION).tar.gz
CDH_PARCEL_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package/bigtop-repos/apt
CDH_PARCEL_BASE_REF=cdh5-base-0.6.0
CDH_PARCEL_BUILD_REF=HEAD
CDH_PARCEL_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package/bigtop-packages/src
$(eval $(call PACKAGE,cdh-parcel,CDH_PARCEL))
CDH_PARCEL_PKG_VERSION=$(CDH_PARCEL_BASE_VERSION)

# Crunch
CRUNCH_NAME=crunch
CRUNCH_RELNOTES_NAME=Apache Crunch
CRUNCH_PKG_NAME=crunch
CRUNCH_BASE_VERSION=0.10.0
CRUNCH_RELEASE_VERSION=1
CRUNCH_TARBALL_DST=crunch-$(CRUNCH_BASE_VERSION).tar.gz
CRUNCH_TARBALL_SRC=apache-crunch-$(CRUNCH_BASE_VERSION)-src.tar.gz
CRUNCH_GIT_REPO=$(REPO_DIR)/cdh5/crunch
CRUNCH_BASE_REF=cdh5-base-$(CRUNCH_BASE_VERSION)
CRUNCH_BUILD_REF=HEAD
CRUNCH_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package/bigtop-packages/src
CRUNCH_SITE=$(CLOUDERA_ARCHIVE)
$(eval $(call PACKAGE,crunch,CRUNCH))

###############
## GPLExtras ##
###############

# Hadoop-LZO
HADOOP_LZO_NAME=hadoop-lzo
HADOOP_LZO_RELNOTES_NAME=Hadoop LZO
HADOOP_LZO_PKG_NAME=hadoop-lzo
HADOOP_LZO_BASE_VERSION=0.4.15
HADOOP_LZO_RELEASE_VERSION=1
HADOOP_LZO_TARBALL_DST=$(HADOOP_LZO_NAME)-$(HADOOP_LZO_BASE_VERSION).tar.gz
HADOOP_LZO_GIT_REPO=$(REPO_DIR)/cdh5/hadoop-lzo
HADOOP_LZO_BUILD_REF=HEAD
HADOOP_LZO_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package/bigtop-packages/src
$(eval $(call PACKAGE,hadoop-lzo,HADOOP_LZO))

# Impala-LZO
IMPALA_LZO_NAME=impala-lzo
IMPALA_LZO_RELNOTES_NAME=Impala LZO
IMPALA_LZO_PKG_NAME=impala-lzo
IMPALA_LZO_BASE_VERSION=1.3.1
IMPALA_LZO_RELEASE_VERSION=1
IMPALA_LZO_TARBALL_DST=$(IMPALA_LZO_NAME)-$(IMPALA_LZO_BASE_VERSION).tar.gz
IMPALA_LZO_GIT_REPO=$(REPO_DIR)/cdh5/impala-lzo
IMPALA_LZO_BUILD_REF=HEAD
IMPALA_LZO_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package/bigtop-packages/src
$(eval $(call PACKAGE,impala-lzo,IMPALA_LZO))

# GPLExtras parcel packages
GPLEXTRAS_PARCEL_NAME=gplextras-parcel
GPLEXTRAS_PARCEL_RELNOTES_NAME=GPLEXTRAS-Parcel
GPLEXTRAS_PARCEL_BASE_VERSION=5.2.0
GPLEXTRAS_PARCEL_PKG_VERSION=$(GPLEXTRAS_PARCEL_BASE_VERSION)
GPLEXTRAS_PARCEL_PKG_NAME=gplextras-parcel-$(GPLEXTRAS_PARCEL_BASE_VERSION)
GPLEXTRAS_PARCEL_RELEASE_VERSION=1
GPLEXTRAS_PARCEL_TARBALL_DST=$(GPLEXTRAS_PARCEL_NAME)-$(GPLEXTRAS_PARCEL_BASE_VERSION).tar.gz
GPLEXTRAS_PARCEL_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package/bigtop-repos/apt
GPLEXTRAS_PARCEL_BUILD_REF=HEAD
GPLEXTRAS_PARCEL_PACKAGE_GIT_REPO=$(REPO_DIR)/cdh5/cdh-package/bigtop-packages/src
$(eval $(call PACKAGE,gplextras-parcel,GPLEXTRAS_PARCEL))

