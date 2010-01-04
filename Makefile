BASE_DIR  :=$(shell pwd)
BUILD_DIR ?=$(BASE_DIR)/build
DL_DIR    ?=$(BASE_DIR)/dl
OUTPUT_DIR?=$(BASE_DIR)/output
CONFIG    ?=$(BASE_DIR)/config.mk

REQUIRED_DIRS = $(BUILD_DIR) $(DL_DIR) $(OUTPUT_DIR)
_MKDIRS :=$(shell for d in $(REQUIRED_DIRS); \
  do                               \
    [ -d $$d ] || mkdir -p $$d;  \
  done) 

TARGETS:=
TARGETS_HELP:=
TARGETS_CLEAN:=

# Pull in the config variables
-include $(CONFIG)
ifndef JAVA32_HOME
$(error Please set JAVA32_HOME in $(CONFIG) or environment)
endif
ifndef JAVA64_HOME
$(error Please set JAVA64_HOME in $(CONFIG) or environment)
endif
ifndef JAVA5_HOME
$(error Please set JAVA5_HOME in $(CONFIG) or environment)
endif
ifndef FORREST_HOME
$(error Please set FORREST_HOME in $(CONFIG) or environment)
endif

# Default Apache mirror
APACHE_MIRROR ?= http://mirror.cloudera.com/apache/

# Include the implicit rules and functions for building packages
include package.mk

help: package-help

all: packages
world: all

# Hadoop 0.18.3-based hadoop package
HADOOP18_NAME=hadoop
HADOOP18_PKG_NAME=hadoop-0.18
HADOOP18_BASE_VERSION=0.18.3
HADOOP18_SOURCE=hadoop-$(HADOOP18_BASE_VERSION).tar.gz
HADOOP18_SOURCE_MD5=dab91dd836fc5d6564b63550f0a0e6ee
HADOOP18_SITE=$(APACHE_MIRROR)/hadoop/core/hadoop-$(HADOOP18_BASE_VERSION)
HADOOP18_GIT_REPO=$(BASE_DIR)/repos/hadoop-0.18
# jdiff workaround... bother.
HADOOP18_BASE_REF=release-0.18.3-with-jdiff
HADOOP18_BUILD_REF=cdh-$(HADOOP18_BASE_VERSION)
HADOOP18_PACKAGE_GIT_REPO=$(BASE_DIR)/repos/hadoop-0.18-package
$(eval $(call PACKAGE,hadoop18,HADOOP18))

# Hadoop 0.20.0-based hadoop package
HADOOP20_NAME=hadoop
HADOOP20_PKG_NAME=hadoop-0.20
HADOOP20_BASE_VERSION=0.20.1
HADOOP20_SOURCE=hadoop-$(HADOOP20_BASE_VERSION).tar.gz
HADOOP20_SOURCE_MD5=719e169b7760c168441b49f405855b72
HADOOP20_SITE=$(APACHE_MIRROR)/hadoop/core/hadoop-$(HADOOP20_BASE_VERSION)
HADOOP20_GIT_REPO=$(BASE_DIR)/repos/hadoop-0.20
HADOOP20_BASE_REF=cdh-base-$(HADOOP20_BASE_VERSION)
HADOOP20_BUILD_REF=HEAD
HADOOP20_PACKAGE_GIT_REPO=$(BASE_DIR)/repos/hadoop-0.20-package
$(eval $(call PACKAGE,hadoop20,HADOOP20))

# Pig 
PIG_BASE_VERSION=0.5.0
PIG_NAME=pig
PIG_PKG_NAME=hadoop-pig
PIG_SOURCE=pig-0.5.0.tar.gz
PIG_GIT_REPO=$(BASE_DIR)/repos/pig
PIG_BASE_REF=cdh-base-$(PIG_BASE_VERSION)
PIG_BUILD_REF=cdh-$(PIG_BASE_VERSION)
PIG_PACKAGE_GIT_REPO=$(BASE_DIR)/repos/pig-package
PIG_SITE=file://$(BASE_DIR)/repos/pristine
$(eval $(call PACKAGE,pig,PIG))

# Hive
HIVE_NAME=hive
HIVE_PKG_NAME=hadoop-hive
HIVE_BASE_VERSION=0.4.0
HIVE_SOURCE=hive-$(HIVE_BASE_VERSION)-hadoop-0.20.0-dev.tar.gz
HIVE_GIT_REPO=$(BASE_DIR)/repos/hive
HIVE_BASE_REF=cdh-base-$(HIVE_BASE_VERSION)
HIVE_BUILD_REF=cdh-$(HIVE_BASE_VERSION)
HIVE_PACKAGE_GIT_REPO=$(BASE_DIR)/repos/hive-package
HIVE_SITE=$(APACHE_MIRROR)/hadoop/hive/hive-$(HIVE_BASE_VERSION)/
$(eval $(call PACKAGE,hive,HIVE))

HIVE_ORIG_SOURCE_DIR=$(HIVE_BUILD_DIR)/source
HIVE_SOURCE_DIR=$(HIVE_BUILD_DIR)/source/src

$(HIVE_TARGET_PREP):
	mkdir -p $($(PKG)_SOURCE_DIR)
	$(BASE_DIR)/tools/setup-package-build $($(PKG)_GIT_REPO) $($(PKG)_BASE_REF) $($(PKG)_BUILD_REF) $(DL_DIR)/$($(PKG)_SOURCE) $(HIVE_BUILD_DIR)/source
	rsync -av $(HIVE_ORIG_SOURCE_DIR)/cloudera/ $(HIVE_SOURCE_DIR)/cloudera/
	touch $@

packages: $(TARGETS) 

help-header:
	@echo "CDH targets:"
	@echo "    all (or world)"

package-help: help-header $(TARGETS_HELP)

clean: $(TARGETS_CLEAN)
	-rm -rf $(BUILD_DIR)

realclean: clean
	-rm -rf $(OUTPUT_DIR)
	-rm -rf $(DL_DIR)

.PHONY: realclean clean package-help help-header packages all world help
