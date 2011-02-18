# Implicit targets
SHELL := /bin/bash

# Download
$(BUILD_DIR)/%/.download:
	mkdir -p $(@D)
	[ -f $($(PKG)_DOWNLOAD_DST) ] || (cd $(DL_DIR) && curl -# -L -o $($(PKG)_TARBALL_DST) $($(PKG)_DOWNLOAD_URL))
	touch $@

# Prep
$(BUILD_DIR)/%/.prep:
	mkdir -p $($(PKG)_SOURCE_DIR)
	$(BASE_DIR)/tools/setup-package-build \
	  $($(PKG)_GIT_REPO) \
	  $($(PKG)_BASE_REF) \
	  $($(PKG)_BUILD_REF) \
	  $($(PKG)_DOWNLOAD_DST) \
	  $($(PKG)_SOURCE_DIR) \
	  $($(PKG)_FULL_VERSION)
	touch $@

# Patch
$(BUILD_DIR)/%/.patch:
	$($(PKG)_SOURCE_DIR)/cloudera/apply-patches \
	  $($(PKG)_SOURCE_DIR) \
	  $($(PKG)_SOURCE_DIR)/cloudera/patches
	touch $@

# Build
$(BUILD_DIR)/%/.build:
	/usr/bin/env \
	  -u DISPLAY \
	  JAVA32_HOME=$(JAVA32_HOME) \
	  JAVA64_HOME=$(JAVA64_HOME) \
	  JAVA5_HOME=$(JAVA5_HOME) \
	  FORREST_HOME=$(FORREST_HOME) \
	  FULL_VERSION=$($(PKG)_FULL_VERSION) \
	  $($(PKG)_SOURCE_DIR)/cloudera/do-release-build
	mkdir -p $($(PKG)_OUTPUT_DIR)
	cp $($(PKG)_SOURCE_DIR)/build/$($(PKG)_NAME)-$($(PKG)_FULL_VERSION).tar.gz $($(PKG)_OUTPUT_DIR)
	touch $@

# Make source RPMs
$(BUILD_DIR)/%/.srpm:
	-rm -rf $(PKG_BUILD_DIR)/rpm/
	mkdir -p $(PKG_BUILD_DIR)/rpm/
	cp -r $($(PKG)_PACKAGE_GIT_REPO)/rpm/topdir $(PKG_BUILD_DIR)/rpm
	mkdir -p $(PKG_BUILD_DIR)/rpm/topdir/{INSTALL,SOURCES,BUILD}
	cp $($(PKG)_OUTPUT_DIR)/$($(PKG)_NAME)-$($(PKG)_FULL_VERSION).tar.gz $(PKG_BUILD_DIR)/rpm/topdir/SOURCES
	$(BASE_DIR)/tools/create_rpms \
	  $($(PKG)_NAME) \
	  $(PKG_BUILD_DIR)/rpm/topdir/INSTALL \
	  $(PKG_BUILD_DIR)/rpm/topdir \
	  $($(PKG)_BASE_VERSION) \
	  $(PKG_FULL_VERSION) \
	  $($(PKG)_PKG_VERSION) \
	  $($(PKG)_RELEASE)
	cp $(PKG_BUILD_DIR)/rpm/topdir/SRPMS/$($(PKG)_PKG_NAME)-$($(PKG)_PKG_VERSION)-$($(PKG)_RELEASE).src.rpm \
	   $($(PKG)_OUTPUT_DIR)
	touch $@

# Make binary RPMs
$(BUILD_DIR)/%/.rpm: SRCRPM=$($(PKG)_OUTPUT_DIR)/$($(PKG)_PKG_NAME)-$($(PKG)_PKG_VERSION)-$($(PKG)_RELEASE).src.rpm
$(BUILD_DIR)/%/.rpm:
	rpmbuild --define "_topdir $(PKG_BUILD_DIR)/rpm/topdir" --rebuild $(SRCRPM)
	rpmbuild --define "_topdir $(PKG_BUILD_DIR)/rpm/topdir" --rebuild --target noarch $(SRCRPM)
	touch $@

# Make source DEBs
$(BUILD_DIR)/%/.sdeb:
	-rm -rf $(PKG_BUILD_DIR)/deb/
	mkdir -p $(PKG_BUILD_DIR)/deb/
	cp $($(PKG)_OUTPUT_DIR)/$($(PKG)_NAME)-$(PKG_FULL_VERSION).tar.gz \
	  $(PKG_BUILD_DIR)/deb/$($(PKG)_PKG_NAME)_$(PKG_PKG_VERSION).orig.tar.gz
	cd $(PKG_BUILD_DIR)/deb && \
	  tar -xvf $($(PKG)_PKG_NAME)_$(PKG_PKG_VERSION).orig.tar.gz && \
	  mv $($(PKG)_NAME)-$(PKG_FULL_VERSION) $($(PKG)_NAME)-$(PKG_PKG_VERSION)
	  cd $(PKG_BUILD_DIR)/deb/$($(PKG)_NAME)-$(PKG_PKG_VERSION) && \
	  cp -r $($(PKG)_PACKAGE_GIT_REPO)/deb/debian.$($(PKG)_NAME) debian && \
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
                    $($(PKG)_PKG_NAME)_$(PKG_PKG_VERSION).orig.tar.gz ; \
            do cp $(PKG_BUILD_DIR)/deb/$$file $($(PKG)_OUTPUT_DIR); \
        done
	touch $@

$(BUILD_DIR)/%/.deb: SRCDEB=$($(PKG)_PKG_NAME)_$($(PKG)_PKG_VERSION)-$($(PKG)_RELEASE).dsc
$(BUILD_DIR)/%/.deb:
	cd $($(PKG)_OUTPUT_DIR) && \
		dpkg-source -x $(SRCDEB) && \
		cd $($(PKG)_PKG_NAME)-$(PKG_PKG_VERSION) && \
			debuild \
				--preserve-envvar PATH --preserve-envvar JAVA32_HOME --preserve-envvar JAVA64_HOME \
				--preserve-envvar JAVA5_HOME --preserve-envvar FORREST_HOME --preserve-envvar MAVEN3_HOME \
				-uc -us -b

$(BUILD_DIR)/%/.relnotes:  $($(PKG)_OUTPUT_DIR)/$($(PKG)_NAME)-$($(PKG)_PKG_VERSION).releasenotes.html
$(BUILD_DIR)/%/.relnotes:
	mkdir -p $(PKG_BUILD_DIR)
	$(BASE_DIR)/tools/relnotes/relnote-gen.sh \
		$($(PKG)_OUTPUT_DIR) \
		$($(PKG)_GIT_REPO) \
		"$($(PKG)_BASE_REF)..HEAD" \
		"CDH $(CDH_VERSION)" \
		"$($(PKG)_BASE_VERSION)" \
		"$($(PKG)_NAME)-$($(PKG)_PKG_VERSION)" \
		"$($(PKG)_RELNOTES_NAME)"
	touch $@

# Package make function
# $1 is the target prefix, $2 is the variable prefix
define PACKAGE

# The default PKG_NAME will be the target prefix
$(2)_NAME           ?= $(1)

# For deb packages, the name of the package itself
$(2)_PKG_NAME       ?= $$($(2)_NAME)

# The default PKG_RELEASE will be 1 unless specified
$(2)_RELEASE        ?= 1

# Calculate the full version based on the git patches
$(2)_FULL_VERSION   = $$($(2)_BASE_VERSION)-CDH3B4-SNAPSHOT
$(2)_PKG_VERSION   := $(shell cd $($(2)_GIT_REPO) && $(BASE_DIR)/tools/branch-tool version)
$(2)_BUILD_REF      := $(notdir $(shell cd $($(2)_GIT_REPO) && git symbolic-ref --quiet HEAD))

$(2)_BUILD_DIR      = $(BUILD_DIR)/$(CDH)/$(1)/$$($(2)_FULL_VERSION)/
$(2)_OUTPUT_DIR      = $(OUTPUT_DIR)/$(CDH)/$(1)
$(2)_SOURCE_DIR       = $$($(2)_BUILD_DIR)/source

# Download source URL and destination path
$(2)_DOWNLOAD_URL = $($(2)_SITE)/$($(2)_TARBALL_SRC)
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

# We download target when the source is not in the download directory
$(1)-download: $$($(2)_TARGET_DL)

# To prep target, we need to download it first
$(1)-prep: $(1)-download $$($(2)_TARGET_PREP)

# To patch target, we need to prep it first
$(1)-patch: $(1)-prep $$($(2)_TARGET_PATCH)

# To build target, we need to patch it first
$(1): $(1)-patch $$($(2)_TARGET_BUILD) $$($(2)_HOOK_POST_BUILD)

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
