# Copyright (c) 2010 Cloudera, inc.
import cloudera.packaging.packaging
import yum


class YumPackage:
    '''
    See L{cloudera.packaging.debian.AptPackage} for documentation
    '''

    def __init__(self, yum_package):
      self.yum_package = yum_package


    def name(self):
      return self.yum_package.name


    def files(self):
      return self.yum_package.files


    def version(self):
      return self.yum_package.printVer()


    def current_architecture(self):
      (rc, output) = cloudera.utils.simple_exec2(["uname", "-m"])
      str = ''.join([line for line in output])
      return str.strip()


    def set_preferred_arch(self, arch):

      if arch == 'current':
        arch = self.current_architecture()

      self.preferred_arch = arch


class YumPackageManager:
    '''
    See L{cloudera.packaging.debian.AptPackageManager} for documentation
    '''

    def __init__(self):
      pass


    def search_from_name(self, package_name):

      yum.YumBase.__init__(self)
      searchlist = ['name']
      matching = self.searchGenerator(searchlist, package_name, showdups=False)
      results = [pkg for (pkg, matched_value) in matching if pkg.name == package_name]
      results.sort()
      return [YumPackage(package) for package in results]


    def install(self, packages):

      for package in packages:
         yum.YumBase.install(self, package.yum_package)

      # build and process the batch transaction
      self.buildTransaction()
      self.processTransaction()

    def uninstall(self, packages):

      for package in packages:
        self.remove(package.yum_package)

      # build and process the batch transaction
      self.buildTransaction()
      self.processTransaction()


    def is_package_installed(self, pkg_name):

      return self.isPackageInstalled(pkg_name)

