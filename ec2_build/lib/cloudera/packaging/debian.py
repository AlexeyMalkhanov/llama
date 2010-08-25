# Copyright (c) 2010 Cloudera, inc.

import cloudera.packaging.packaging
import apt


class AptPackage:
  '''
  Apt package
  '''

  def __init__(self, apt_package):
    self.package = apt_package


  def files(self):
    '''
    Return the list of files installed
    '''
    return self.package.installed_files


  def name(self):
    '''
    Return package name
    @return Package name
    '''
    return self.package.name


  def version(self):
    '''
    Return Version
    @return Version
    '''
    return self.package.installedVersion


  def current_architecture(self):
    '''
    Return current architecture
    @return Current architecture
    '''
    (rc, output) = cloudera.utils.simple_exec2(["uname", "-m"])
    str = ''.join([line for line in output])
    return str.strip()


  def set_preferred_arch(self, arch):
    '''
    Set preferred architecture
    @param arch Preferred architecture
    '''

    if arch == 'current':
      arch = self.current_architecture()

    self.preferred_arch = arch


  def is_installed(self)
    '''
    Check if the package is already installed
    @return Boolean indicateing whether it is isntalled or not
    '''
    return self.package.is_installed


class AptPackageManager:
    '''
    Package manager for Apt platform
    '''

    def __init__(self):
      self.cache = apt.cache.Cache()


    def search_from_name(self, package_name):
      '''
      @param package_name Package to look for
      @return List of Package
      '''
      if self.cache.has_key(package_name):
        return [AptPackage(self.cache[package_name])]
      else:
        return []


    def install(self, packages):
      '''
      @param packages List of packages
      '''

      for package in packages:
        package.package.mark_install()

      self.cache.commit(apt.progress.TextFetchProgress(), apt.progress.InstallProgress())


    def uninstall(self, packages):
      '''
      @param packages List of packages
      '''

      for package in packages:
        package.package.mark_delete()

      self.cache.commit(apt.progress.TextFetchProgress(), apt.progress.InstallProgress())


    def is_package_installed(self, pkg_name):
      '''
      @param pkg_name Package name
      @return Boolean. True if installed. False otherwise (or zero ore more than one package found)
      '''

      pkg = self.search_from_name(pkg_name)

      if len(pkg) == 1:
        return pkg[0].is_installed
      else:
        return False

