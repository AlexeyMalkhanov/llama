# Implicit targets
SHELL := /bin/bash

COMPONENT_HASH=$(shell cd $($(PKG)_GIT_REPO) && git rev-parse HEAD)
PACKAGING_HASH=$(shell cd $(CDH_PACKAGE_GIT_REPO) && git rev-parse HEAD)
CDH_HASH=$(shell git rev-parse HEAD)

# Download
$(BUILD_DIR)/%/.download:
	mkdir -p $(@D)
	[ -z "$($(PKG)_TARBALL_SRC)" -o -f $($(PKG)_DOWNLOAD_DST) ] || (cd $(DL_DIR) && curl -k -# -L -o $($(PKG)_TARBALL_DST) $($(PKG)_DOWNLOAD_URL))
	touch $@

# Prep
$(BUILD_DIR)/%/.prep:
	mkdir -p $($(PKG)_SOURCE_DIR)
	if [ ! -z "$($(PKG)_TARBALL_SRC)" ] && [ -z "$($(PKG)_TARBALL_ONLY)" ]; then \
	  $(BASE_DIR)/tools/setup-package-build \
	    $($(PKG)_GIT_REPO) \
	    $($(PKG)_BASE_REF) \
	    $($(PKG)_BUILD_REF) \
	    $($(PKG)_DOWNLOAD_DST) \
	    $($(PKG)_SOURCE_DIR) \
	    $($(PKG)_FULL_VERSION) \
	    $($(PKG)_NAME) \
	    $($(PKG)_PKG_VERSION) \
	    $($(PKG)_RELEASE) \
	    $(CDH_VERSION_STRING) \
	    $(COMPONENT_HASH) \
	    $(PACKAGING_HASH) \
	    $(CDH_HASH) \
	    $($(PKG)_SRC_PREFIX); \
	else \
	  mkdir -p $($(PKG)_SOURCE_DIR)/cloudera; \
          $(BASE_DIR)/tools/generate-build-properties \
	    $($(PKG)_GIT_REPO) \
	    $($(PKG)_BASE_REF) \
	    $($(PKG)_BUILD_REF) \
	    $($(PKG)_SOURCE_DIR)/cloudera/build.properties \
	    $($(PKG)_FULL_VERSION) \
	    $($(PKG)_PKG_VERSION) \
	    $($(PKG)_RELEASE) \
	    $($(PKG)_NAME) \
	    $(CDH_VERSION_STRING) \
	    $(COMPONENT_HASH) \
	    $(PACKAGING_HASH) \
	    $(CDH_HASH); \
	fi ;
	# Special logic below for cases with source we want to copy, but without pristine tarballs.
	if [ -z "$($(PKG)_TARBALL_SRC)" ] && [ ! -z "$($(PKG)_TARBALL_DST)" ]; then \
	  cp -r $($(PKG)_GIT_REPO)/* $($(PKG)_SOURCE_DIR); \
	fi ;
	# More special logic for pristine tarball but no source git repo
	[ -z "$($(PKG)_TARBALL_ONLY)" ] || tar  --strip-components 1 -xf "$($(PKG)_DOWNLOAD_DST)" -C "$($(PKG)_SOURCE_DIR)"
	touch $@

# Patch
$(BUILD_DIR)/%/.patch:
	[ -z "$($(PKG)_TARBALL_SRC)" -o -n "$($(PKG)_TARBALL_ONLY)" ] || $($(PKG)_SOURCE_DIR)/cloudera/apply-patches \
	  $($(PKG)_SOURCE_DIR) \
	  $($(PKG)_SOURCE_DIR)/cloudera/patches
	touch $@

# Build
$(BUILD_DIR)/%/.build:
	# Hack - use tarball dst here because we want to do the build for CM, but not for bigtop-utils.
	cd $($(PKG)_SOURCE_DIR) ;\
	[ -z "$($(PKG)_TARBALL_DST)" ] || /usr/bin/env \
	  -u DISPLAY \
	  JAVA5_HOME=$(JAVA5_HOME) \
	  FORREST_HOME=$(FORREST_HOME) \
	  THRIFT_HOME=$(THRIFT_HOME) \
	  NODE_HOME=$(NODE_HOME) \
	  GIT_REPO=$($(PKG)_GIT_REPO) \
	  FULL_VERSION=$($(PKG)_FULL_VERSION) \
	  COMPONENT_HASH=$(COMPONENT_HASH) \
	  $($(PKG)_PACKAGE_GIT_REPO)/common/$($(PKG)_NAME)/do-component-build
	mkdir -p $($(PKG)_OUTPUT_DIR)
	[ -z "$($(PKG)_TARBALL_DST)" ] || \
	  cp $($(PKG)_SOURCE_DIR)/build/$($(PKG)_NAME)-$($(PKG)_FULL_VERSION).tar.gz $($(PKG)_OUTPUT_DIR)
	touch $@

# Maven deploy (for version changes)
$(BUILD_DIR)/%/.maven:
	# Hack - use tarball dst here because we want to do the build for CM, but not for bigtop-utils.
	cd $($(PKG)_SOURCE_DIR) ;\
	[ -z "$($(PKG)_TARBALL_DST)" ] || /usr/bin/env \
	  -u DISPLAY \
	  JAVA5_HOME=$(JAVA5_HOME) \
	  FORREST_HOME=$(FORREST_HOME) \
	  THRIFT_HOME=$(THRIFT_HOME) \
	  NODE_HOME=$(NODE_HOME) \
	  MAVEN_ONLY=true \
	  FULL_VERSION=$($(PKG)_FULL_VERSION) \
	  COMPONENT_HASH=$(COMPONENT_HASH) \
	  $($(PKG)_PACKAGE_GIT_REPO)/common/$($(PKG)_NAME)/do-component-build
	touch $@

# Make source RPMs
$(BUILD_DIR)/%/.srpm:
	-rm -rf $(PKG_BUILD_DIR)/rpm/
	mkdir -p $(PKG_BUILD_DIR)/rpm/{INSTALL,SOURCES,BUILD,SRPMS,RPMS}
	cp -r $($(PKG)_PACKAGE_GIT_REPO)/rpm/$($(PKG)_NAME)/* $(PKG_BUILD_DIR)/rpm
	cp -r $($(PKG)_PACKAGE_GIT_REPO)/common/$($(PKG)_NAME)/* $(PKG_BUILD_DIR)/rpm/SOURCES
	cp $($(PKG)_PACKAGE_GIT_REPO)/templates/* $(PKG_BUILD_DIR)/rpm/SOURCES/
	# FIXME: BIGTOP-292
	cd $($(PKG)_PACKAGE_GIT_REPO)/common/$($(PKG)_NAME) ; tar -czf $(PKG_BUILD_DIR)/rpm/SOURCES/$($(PKG)_NAME)-bigtop-packaging.tar.gz *
	[ -z "$($(PKG)_TARBALL_DST)" ] || \
	  cp $($(PKG)_OUTPUT_DIR)/$($(PKG)_NAME)-$($(PKG)_FULL_VERSION).tar.gz $(PKG_BUILD_DIR)/rpm/SOURCES
	[ -d $($(PKG)_PACKAGE_GIT_REPO)/common/$($(PKG)_NAME) ] && \
		cp -r $($(PKG)_PACKAGE_GIT_REPO)/common/$($(PKG)_NAME)/* $(PKG_BUILD_DIR)/rpm/SOURCES
	sed -i -e 's/^%build/%build\nexport COMPONENT_HASH=$(COMPONENT_HASH)/' $(PKG_BUILD_DIR)/rpm/SPECS/$($(PKG)_NAME).spec
	sed -i -e '1i\
$(EXTRA_VAR_DEFS) \
%define $(subst -,_,$($(PKG)_NAME))_version $($(PKG)_PKG_VERSION) \
%define $(subst -,_,$($(PKG)_NAME))_patched_version $($(PKG)_FULL_VERSION) \
%define $(subst -,_,$($(PKG)_NAME))_base_version $($(PKG)_BASE_VERSION) \
%define $(subst -,_,$($(PKG)_NAME))_release $($(PKG)_RELEASE)%{?dist} \
%define cdh_customer_patch p$(CDH_CUSTOMER_PATCH) \
%define cdh_parcel_custom_version $($(PKG)_PKG_VERSION)-$($(PKG)_RELEASE)%{?dist}' $(PKG_BUILD_DIR)/rpm/SPECS/$($(PKG)_NAME).spec
	env COMPONENT_HASH=$(COMPONENT_HASH) \
	rpmbuild --define "_topdir $(PKG_BUILD_DIR)/rpm/" -bs --nodeps --buildroot="$(PKG_BUILD_DIR)/rpm/INSTALL" \
                                                                       $(PKG_BUILD_DIR)/rpm/SPECS/$($(PKG)_NAME).spec
	$(PKG)_RELEASE_DIST=$(shell rpmbuild --eval '%{?dist}' 2>/dev/null); \
	cp $(PKG_BUILD_DIR)/rpm/SRPMS/$($(PKG)_PKG_NAME)-$($(PKG)_PKG_VERSION)-$($(PKG)_RELEASE)$${$(PKG)_RELEASE_DIST}.src.rpm \
	   $($(PKG)_OUTPUT_DIR)
	touch $@

# Make binary RPMs
$(BUILD_DIR)/%/.rpm:
	$(PKG)_RELEASE_DIST=$(shell rpmbuild --eval '%{?dist}' 2>/dev/null); \
	SRCRPM=$($(PKG)_OUTPUT_DIR)/$($(PKG)_PKG_NAME)-$($(PKG)_PKG_VERSION)-$($(PKG)_RELEASE)$${$(PKG)_RELEASE_DIST}.src.rpm ; \
	env COMPONENT_HASH=$(COMPONENT_HASH) \
	rpmbuild --define "_topdir $(PKG_BUILD_DIR)/rpm/" --rebuild $${SRCRPM}
	touch $@

# Make source DEBs
$(BUILD_DIR)/%/.sdeb:
	-rm -rf $(PKG_BUILD_DIR)/deb/
	mkdir -p $(PKG_BUILD_DIR)/deb/
	cd $(PKG_BUILD_DIR)/deb && \
          mkdir $($(PKG)_NAME)-$(PKG_PKG_VERSION) ;\
	  if [ -n "$($(PKG)_TARBALL_DST)" ]; then \
	    cp $($(PKG)_OUTPUT_DIR)/$($(PKG)_NAME)-$(PKG_FULL_VERSION).tar.gz \
	       $(PKG_BUILD_DIR)/deb/$($(PKG)_PKG_NAME)_$(PKG_PKG_VERSION).orig.tar.gz ;\
	    tar -C $($(PKG)_NAME)-$(PKG_PKG_VERSION) --strip-components 1 \
                -xzvf $($(PKG)_PKG_NAME)_$(PKG_PKG_VERSION).orig.tar.gz  ;\
	  else \
            tar -czf $(PKG_BUILD_DIR)/deb/$($(PKG)_PKG_NAME)_$(PKG_PKG_VERSION).orig.tar.gz \
                  $($(PKG)_NAME)-$(PKG_PKG_VERSION) ;\
          fi ;\
	cd $(PKG_BUILD_DIR)/deb/$($(PKG)_NAME)-$(PKG_PKG_VERSION) && \
          cp -r $($(PKG)_PACKAGE_GIT_REPO)/deb/$($(PKG)_NAME) debian && \
	echo '#!/bin/bash' > debian/tar_build_env.sh && \
	echo "$(EXTRA_VAR_DEFS)" >> debian/tar_build_env.sh && \
	echo "export COMPONENT_HASH=$(COMPONENT_HASH)" >> debian/tar_build_env.sh \
	echo "PKG_VERSION=$($(PKG)_PKG_VERSION)" >> debian/tar_build_env.sh && \
	echo "FULL_VERSION=$($(PKG)_FULL_VERSION)" >> debian/tar_build_env.sh && \
	echo "BASE_VERSION=$($(PKG)_BASE_VERSION)" >> debian/tar_build_env.sh && \
	echo "PKG_RELEASE=$($(PKG)_RELEASE)" >> debian/tar_build_env.sh && \
	echo "CDH_CUSTOMER_PATCH=p$(CDH_CUSTOMER_PATCH)" >> debian/tar_build_env.sh && \
	echo "CDH_PARCEL_CUSTOM_VERSION=$($(PKG)_PKG_VERSION)-$($(PKG)_RELEASE).$(shell lsb_release -sc)" >> debian/tar_build_env.sh && \
	sed -i -e '/^#!/a\
$(EXTRA_VAR_DEFS) \
export COMPONENT_HASH=$(COMPONENT_HASH) \
$(PKG)_VERSION=$($(PKG)_PKG_VERSION) \
$(PKG)_PATCHED_VERSION=$($(PKG)_FULL_VERSION) \
$(PKG)_BASE_VERSION=$($(PKG)_BASE_VERSION) \
$(PKG)_RELEASE=$($(PKG)_RELEASE) \
CDH_CUSTOMER_PATCH=p$(CDH_CUSTOMER_PATCH) \
CDH_PARCEL_CUSTOM_VERSION=$($(PKG)_PKG_VERSION)-$($(PKG)_RELEASE).$(shell lsb_release -sc)' debian/rules && \
	  cp $($(PKG)_PACKAGE_GIT_REPO)/templates/* debian && \
	  cp -r $($(PKG)_PACKAGE_GIT_REPO)/common/$($(PKG)_NAME)/* debian && \
	  find debian -name "*.[ex,EX,~]" | xargs rm -f && \
	  $(BASE_DIR)/tools/generate-debian-changelog \
	    $($(PKG)_GIT_REPO) \
	    $($(PKG)_BASE_REF) \
	    $($(PKG)_BUILD_REF) \
	    $($(PKG)_PKG_NAME) \
	    $($(PKG)_RELEASE) \
	    debian/changelog \
	    $($(PKG)_PKG_VERSION) && \
	  dpkg-buildpackage -uc -us -sa -S
	for file in $($(PKG)_PKG_NAME)_$(PKG_PKG_VERSION)-$($(PKG)_RELEASE).dsc \
                    $($(PKG)_PKG_NAME)_$(PKG_PKG_VERSION)-$($(PKG)_RELEASE).diff.gz \
                    $($(PKG)_PKG_NAME)_$(PKG_PKG_VERSION)-$($(PKG)_RELEASE)_source.changes \
                    $($(PKG)_PKG_NAME)_$(PKG_PKG_VERSION)-$($(PKG)_RELEASE).debian.tar.gz \
                    $($(PKG)_PKG_NAME)_$(PKG_PKG_VERSION).orig.tar.gz ; \
            do cp $(PKG_BUILD_DIR)/deb/$$file $($(PKG)_OUTPUT_DIR); \
        done
	touch $@

$(BUILD_DIR)/%/.deb: SRCDEB=$($(PKG)_PKG_NAME)_$($(PKG)_PKG_VERSION)-$($(PKG)_RELEASE).dsc
$(BUILD_DIR)/%/.deb:
	cd $($(PKG)_OUTPUT_DIR) && \
		dpkg-source -x $(SRCDEB) && \
		cd $($(PKG)_PKG_NAME)-$(PKG_PKG_VERSION) && \
			env COMPONENT_HASH=$(COMPONENT_HASH) \
			debuild \
				--preserve-envvar PATH \
				--preserve-envvar JAVA5_HOME --preserve-envvar FORREST_HOME --preserve-envvar MAVEN3_HOME \
				--preserve-envvar THRIFT_HOME --preserve-envvar JAVA_HOME --preserve-envvar GIT_REPO \
				--preserve-envvar NODE_HOME --preserve-envvar SCALA_HOME -uc -us -b
	touch $@

$(BUILD_DIR)/%/.relnotes:  $($(PKG)_OUTPUT_DIR)/$($(PKG)_NAME)-$($(PKG)_PKG_VERSION).releasenotes.html
$(BUILD_DIR)/%/.relnotes:
	mkdir -p $(PKG_BUILD_DIR)
	$(BASE_DIR)/tools/relnotes/relnote-gen.sh \
		$($(PKG)_OUTPUT_DIR) \
		$($(PKG)_GIT_REPO) \
		"$($(PKG)_BASE_REF)..HEAD" \
		"CDH $(LONG_VERSION)" \
		"$($(PKG)_BASE_VERSION)" \
		"$($(PKG)_NAME)-$($(PKG)_FULL_VERSION)" \
		"$($(PKG)_RELNOTES_NAME)" \
		"$($(PKG)_PACKAGE_GIT_REPO)" \
		"$($(PKG)_NAME)" \
		"$(BIGTOP_UTILS_BASE_REF)..HEAD" \
		"$(PREV_RELEASE_TAG)..HEAD"
	touch $@

# FIXME: the following needs to go away once MR1 grafting happens
HADOOP_COMMON_PKG_VERSION=$(shell groovy $(BASE_DIR)/ec2_build/bin/pinMr1DependencyVersion \
                                         --release=$(CDH_REL_STRING)              \
                                         --patch=$(CDH_CUSTOMER_PATCH)              \
                                         --maven-suffix=$(CDH_VERSION_STRING)     \
                                         --project=hadoop --dump)
HADOOP_COMMON_PKG_RELEASE=$(shell groovy $(BASE_DIR)/ec2_build/bin/pinMr1DependencyVersion \
                                         --release=$(CDH_REL_STRING)              \
                                         --patch=$(CDH_CUSTOMER_PATCH)              \
                                         --maven-suffix=$(CDH_VERSION_STRING)     \
                                         --project=hadoop --dump-release)
mr1-sdeb : EXTRA_VAR_DEFS=HADOOP_COMMON_VERSION=$(strip $(HADOOP_COMMON_PKG_VERSION))~$$(shell lsb_release -sc)-$(strip $(HADOOP_COMMON_PKG_RELEASE))
mr1-srpm : EXTRA_VAR_DEFS=%define hadoop_common_version $(strip $(HADOOP_COMMON_PKG_VERSION))%{?dist}

# Package make function
# $1 is the target prefix, $2 is the variable prefix
define PACKAGE

$(2)_BASE_REF ?= $($(2)_BUILD_REF)

# The default PKG_NAME will be the target prefix
$(2)_NAME           ?= $(1)

# For deb packages, the name of the package itself
$(2)_PKG_NAME       ?= $$($(2)_NAME)

CDH_REL_STRING = $(CDH_REL_STRING)
ifneq (, $(CDH_BETA_REL_STRING))
  ifneq ("", $(strip $(CDH_BETA_REL_STRING)))
      CDH_REL_STRING=$(CDH_BETA_REL_STRING)
    endif
endif

GPLEXTRAS_REL_STRING = $(GPLEXTRAS_REL_STRING)
ifneq (, $(GPLEXTRAS_BETA_REL_STRING))
  ifneq ("", $(strip $(GPLEXTRAS_BETA_REL_STRING)))
      GPLEXTRAS_REL_STRING=$(GPLEXTRAS_BETA_REL_STRING)
    endif
endif

ifneq (, $($(2)_GPLEXTRAS))
$(2)_RELEASE        = $$($(2)_RELEASE_VERSION).$$(GPLEXTRAS_REL_STRING).p$(CDH_CUSTOMER_PATCH)$(CDH_BUILD_STAMP)
else
$(2)_RELEASE        = $$($(2)_RELEASE_VERSION).$$(CDH_REL_STRING).p$(CDH_CUSTOMER_PATCH)$(CDH_BUILD_STAMP)
endif

# Calculate the full version based on the git patches
ifneq (, $(CDH_VERSION_STRING))
  ifneq ("", $(strip $(CDH_VERSION_STRING)))
    $(2)_FULL_VERSION   = $$($(2)_BASE_VERSION)-$(CDH_VERSION_STRING)
  endif
endif
$(2)_FULL_VERSION  ?= $$($(2)_BASE_VERSION)

ifneq (, $($(2)_GPLEXTRAS))
$(2)_PKG_VERSION   ?= $(shell cd $($(2)_GIT_REPO) && $(BASE_DIR)/tools/branch-tool version --prefix=$(GPLEXTRAS) $(NO_PATCH_COUNT) $(GPLEXTRAS_REL_STRING))
else
$(2)_PKG_VERSION   ?= $(shell cd $($(2)_GIT_REPO) && $(BASE_DIR)/tools/branch-tool version --prefix=$(CDH) $(NO_PATCH_COUNT) $(CDH_REL_STRING))
endif

ifneq ($(2)_BUILD_REF,$(2)_BASE_REF)
$(2)_BUILD_REF      := $(notdir $(shell cd $($(2)_GIT_REPO) && git symbolic-ref --quiet HEAD))
endif


$(2)_BUILD_DIR      = $(BUILD_DIR)/$(CDH)/$(1)/$$($(2)_FULL_VERSION)/
$(2)_OUTPUT_DIR      = $(OUTPUT_DIR)/$(CDH)/$(1)
$(2)_SOURCE_DIR       = $$($(2)_BUILD_DIR)/source

# Download source URL and destination path
$(2)_DOWNLOAD_URL ?= $($(2)_SITE)/$($(2)_TARBALL_SRC)
$(2)_DOWNLOAD_DST = $(DL_DIR)/$($(2)_TARBALL_DST)

# Define the file stamps
$(2)_TARGET_DL       = $$($(2)_BUILD_DIR)/.download
$(2)_TARGET_PREP     = $$($(2)_BUILD_DIR)/.prep
$(2)_TARGET_PATCH    = $$($(2)_BUILD_DIR)/.patch
$(2)_TARGET_BUILD    = $$($(2)_BUILD_DIR)/.build
$(2)_TARGET_SRPM     = $$($(2)_BUILD_DIR)/.srpm
$(2)_TARGET_RPM      = $$($(2)_BUILD_DIR)/.rpm
$(2)_TARGET_SDEB     = $$($(2)_BUILD_DIR)/.sdeb
$(2)_TARGET_DEB      = $$($(2)_BUILD_DIR)/.deb
$(2)_TARGET_RELNOTES = $$($(2)_BUILD_DIR)/.relnotes
$(2)_TARGET_MAVEN    = $$($(2)_BUILD_DIR)/.maven

# We download target when the source is not in the download directory
$(1)-download: $$($(2)_TARGET_DL)

# To prep target, we need to download it first
$(1)-prep: $(1)-download $$($(2)_TARGET_PREP)

# To patch target, we need to prep it first
$(1)-patch: $(1)-prep $$($(2)_TARGET_PATCH)

# To build target, we need to patch it first
$(1): $(1)-patch $$($(2)_TARGET_BUILD) $$($(2)_HOOK_POST_BUILD)

# To do the Maven-only build target, we need to patch first.
$(1)-maven: $(1)-patch $$($(2)_TARGET_MAVEN)

# To make srpms, we need to build the package
$(1)-srpm: $(1) $$($(2)_TARGET_SRPM)

# To make binary rpms, we need to build source RPMs
$(1)-rpm: $(1)-srpm $$($(2)_TARGET_RPM)

# To make sdebs, we need to build the package
$(1)-sdeb: $(1) $$($(2)_TARGET_SDEB)

# To make debs, we need to make source packages
$(1)-deb: $(1)-sdeb $$($(2)_TARGET_DEB)

# To make the release notes we need to build the target
$(1)-relnotes: $$($(2)_TARGET_RELNOTES)

####
# Helper targets -version -help etc
$(1)-version:
	@echo "Base: $$($(2)_BASE_VERSION)"
	@echo "Full: $$($(2)_FULL_VERSION)"

$(1)-help:
	@echo "    $(1)  [$(1)-version, $(1)-info, $(1)-relnotes,"
	@echo "           $(1)-srpm, $(1)-rpm]"
	@echo "           $(1)-sdeb, $(1)-deb]"

$(1)-clean:
	-rm -rf $(BUILD_DIR)/$(CDH)/$(1)

$(1)-info:
	@echo "Info for package $(1)"
	@echo "  Will download from URL: $$($(2)_DOWNLOAD_URL)"
	@echo "  To destination file: $$($(2)_DOWNLOAD_DST)"
	@echo "  Then unpack into $$($(2)_SOURCE_DIR)"
	@echo
	@echo "Patches:"
	@echo "  BASE_REF: $$($(2)_BASE_REF)"
	@echo "  BUILD_REF: $$($(2)_BUILD_REF)"
	@echo "  Generated from: git log $$($(2)_BASE_REF)..$$($(2)_BUILD_REF) in $$($(2)_GIT_REPO)"
	@echo
	@echo "Git repo: " $$($(2)_GIT_REPO)
	@echo "Currently checked out: " $(shell cd $($(2)_GIT_REPO) && git symbolic-ref --quiet HEAD)
	@echo "Version: $$($(2)_FULL_VERSION)"
	@echo
	@echo "Stamp status:"
	@for mystamp in DL PREP PATCH BUILD SRPM RPM SDEB DEB RELNOTES;\
	  do echo -n "  $$$$mystamp: " ; \
	  ([ -f $($(1)_$$$$mystamp) ] && echo present || echo not present) ; \
	done

# Implicit rules with PKG variable
$$($(2)_TARGET_DL):       PKG=$(2)
$$($(2)_TARGET_PREP):     PKG=$(2)
$$($(2)_TARGET_PREP):     PKG_FULL_VERSION=$$($(2)_FULL_VERSION)
$$($(2)_TARGET_PATCH):    PKG=$(2)
$$($(2)_TARGET_BUILD):    PKG=$(2)
$$($(2)_TARGET_MAVEN):    PKG=$(2)
$$($(2)_TARGET_RPM) $$($(2)_TARGET_SRPM) $$($(2)_TARGET_SDEB) $$($(2)_TARGET_DEB) $$($(2)_TARGET_RELNOTES): PKG=$(2)
$$($(2)_TARGET_RPM) $$($(2)_TARGET_SRPM) $$($(2)_TARGET_SDEB) $$($(2)_TARGET_DEB) $$($(2)_TARGET_RELNOTES): PKG_FULL_VERSION=$$($(2)_FULL_VERSION)
$$($(2)_TARGET_RPM) $$($(2)_TARGET_SRPM) $$($(2)_TARGET_SDEB) $$($(2)_TARGET_DEB) $$($(2)_TARGET_RELNOTES): PKG_PKG_VERSION=$$($(2)_PKG_VERSION)
$$($(2)_TARGET_RPM) $$($(2)_TARGET_SRPM) $$($(2)_TARGET_SDEB) $$($(2)_TARGET_DEB) $$($(2)_TARGET_RELNOTES): PKG_SOURCE_DIR=$$($(2)_SOURCE_DIR)
$$($(2)_TARGET_RPM) $$($(2)_TARGET_SRPM) $$($(2)_TARGET_SDEB) $$($(2)_TARGET_DEB) $$($(2)_TARGET_RELNOTES): PKG_BUILD_DIR=$$($(2)_BUILD_DIR)


TARGETS += $(1)
TARGETS_HELP += $(1)-help
TARGETS_CLEAN += $(1)-clean
TARGETS_SRPM += $(1)-srpm
TARGETS_RPM += $(1)-rpm
TARGETS_SDEB += $(1)-sdeb
TARGETS_DEB += $(1)-deb
TARGETS_RELNOTES += $(1)-relnotes
endef
