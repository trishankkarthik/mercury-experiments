

# 1st-party
import glob
import logging
import os
import re

# 2nd-party
import changelog
from metadatawriter import MetadataWriter
import nouns


class Projects:


  '''Keep state on projects and packages.'''


  def __init__(self, changelog_reader):
    # str: str[64]
    self.__project_to_keyid = {}
    # str: {str (absolute package filename)}
    self.__project_to_packages = {}
    # str: int > 0
    self.__project_to_version = {}
    # str: bool
    self.__project_to_dirty = {}

    # str[64]: str[64]
    self.__keyid_to_keyval = {}

    # str (absolute package filename): str[64]
    self.__package_to_sha256 = {}
    # str (absolute package filename): int > 0
    self.__package_to_length = {}

    self.__setup()
    self.__reverse(changelog_reader)


  def __add_project_and_packages(self, project_name):
    logging.debug(project_name)
    self.add_project(project_name)

    packages_directory = os.path.join(nouns.PACKAGES_DIRECTORY,
                                      '*/*/{}/*'.format(project_name))
    # NOTE: With PyPI renaming/canonical-ization of project names,
    # simple names may not directly correspond to package names. What this
    # means is that there may seem to be no packages for renamed projects.
    for package in sorted(glob.glob(packages_directory)):
      self.add_package(package)


  # Return a *deterministic* "hash" for this package.
  # WARNING: Do *NOT* reuse this value anywhere else!
  def __make_hash_for_package(self, package):
    # Return the hash of the package path.
    return MetadataWriter.get_sha256(package.encode('utf-8'))


  # Return a *deterministic* "keyid" for this project.
  # WARNING: Do *NOT* reuse this value anywhere else!
  def __make_keyid_for_project(self, project_name):
    # It just so happens that a SHA-256 hex digest is as long as our keyid.
    return MetadataWriter.get_sha256(project_name.encode('utf-8'))


  def __mark_project_as_dirty(self, project_name):
    assert self.__project_exists(project_name)
    self.__project_to_dirty[project_name] = True
    logging.debug('Marked project as dirty: {}'.format(project_name))


  def __package_exists(self, package):
    project_name = self.get_project_name_from_package(package)
    # Do NOT call this function without ensuring the existence of the project.
    assert self.__project_exists(project_name)

    if package in self.__project_to_packages[project_name]:
      assert package in self.__package_to_length
      assert package in self.__package_to_sha256
      return True
    else:
      return False


  def __project_exists(self, project_name):
    return project_name in self.__project_to_keyid or \
           project_name in self.__project_to_packages or \
           project_name in self.__project_to_version


  def __reverse(self, changelog_reader):
    logging.debug('Reversing the change log...')

    for change, timestamp in reversed(changelog_reader.filter_changes()):
      if isinstance(change, changelog.AddPackage):
        package = os.path.join(nouns.PACKAGES_DIRECTORY, change.name)
        project_name = self.get_project_name_from_package(package)

        # If the project itself no longer exists now, then there is nothing to
        # reverse.
        if self.__project_exists(project_name):
          if self.__package_exists(package):
            self.remove_package(package)
          else:
            logging.warn('Could not remove non-existent package {} '\
                         'from project {}'.format(package, project_name))
        else:
          logging.warn('Could not remove package {} '\
                        'from non-existent project {}'.format(package,
                                                              project_name))

      elif isinstance(change, changelog.AddProject):
        project_name = change.name

        # If the project itself no longer exists now, then there is nothing to
        # reverse.
        if self.__project_exists(project_name):
          self.remove_project(project_name)
        else:
          logging.warn('Could not remove '\
                       'non-existent project {}'.format(project_name))

      else:
        # Ignore {RemovePackage, RemoveProject}, because if the package/project
        # is now on disk, then we do not want to remove it right now, because
        # we want to remove it later when we replay the change log.
        # Otherwise, if the package/project is not on the disk now, then there
        # is nothing to remove later when we replay the change log.
        assert isinstance(change, changelog.RemovePackage) or \
               isinstance(change, changelog.RemoveProject)

    logging.debug('...done.')


  def __setup(self):
    project_names = \
      sorted(d for d in os.listdir(nouns.SIMPLE_DIRECTORY) \
             if os.path.isdir(os.path.join(nouns.SIMPLE_DIRECTORY, d)))

    for project_name in project_names:
      self.__add_project_and_packages(project_name)


  def add_package(self, package):
    project_name = self.get_project_name_from_package(package)
    assert self.__project_exists(project_name)
    self.__project_to_packages[project_name].add(package)
    self.__package_to_sha256[package] = self.__make_hash_for_package(package)
    self.__package_to_length[package] = os.path.getsize(package)
    self.__mark_project_as_dirty(project_name)
    logging.info('Added package: {}'.format(package))


  def add_project(self, project_name):
    assert not self.__project_exists(project_name)

    keyid = self.__make_keyid_for_project(project_name)
    self.__keyid_to_keyval[keyid] = MetadataWriter.get_random_ed25519_keyval()
    self.__project_to_keyid[project_name] = keyid
    self.__project_to_packages[project_name] = set()
    self.__project_to_version[project_name] = 1
    self.__mark_project_as_dirty(project_name)
    logging.info('Added project: {}'.format(project_name))


  @property
  def dirty(self):
    return [name for name in self.names if self.__project_to_dirty[name]]


  def get_keyids_for_project(self, project_name):
    assert self.__project_exists(project_name)
    return (self.__project_to_keyid[project_name],)


  def get_keyval_for_keyid(self, keyid):
    return self.__keyid_to_keyval[keyid]


  @staticmethod
  def get_project_name_from_package(package):
    return re.match(r'^.*/packages/.+/.+/(.+)/.+$', package).group(1)


  def get_project_version(self, project_name):
    assert self.__project_exists(project_name)
    version = self.__project_to_version[project_name]
    assert version > 0
    return version


  def get_targets_metadata_for_project(self, project_name):
    def get_relpath(package):
      assert package.startswith(nouns.PYPI_DIRECTORY)
      return package[len(nouns.PYPI_DIRECTORY)+1:]

    assert self.__project_exists(project_name)
    return {
      get_relpath(package):
        MetadataWriter.get_target_metadata(self.__package_to_sha256[package],
                                           self.__package_to_length[package])
      for package in self.__project_to_packages[project_name]
    }


  def inc_project_version(self, project_name):
    assert self.__project_exists(project_name)
    self.__project_to_version[project_name] += 1
    self.__mark_project_as_dirty(project_name)
    logging.info('Incremented project version: {}'.format(project_name))


  @property
  def names(self):
    assert self.__project_to_keyid.keys() == self.__project_to_packages.keys()
    assert self.__project_to_keyid.keys() == self.__project_to_version.keys()
    return sorted(self.__project_to_keyid.keys())


  def remove_package(self, package):
    project_name = self.get_project_name_from_package(package)
    assert self.__project_exists(project_name)
    assert package in self.__project_to_packages[project_name]
    assert package in self.__package_to_length
    assert package in self.__package_to_sha256

    self.__project_to_packages[project_name].discard(package)
    del self.__package_to_length[package]
    del self.__package_to_sha256[package]
    self.__mark_project_as_dirty(project_name)

    logging.info('Removed package: {}'.format(package))


  def remove_project(self, project_name):
    assert self.__project_exists(project_name)

    del self.__keyid_to_keyval[self.__project_to_keyid[project_name]]
    del self.__project_to_dirty[project_name]
    del self.__project_to_keyid[project_name]
    del self.__project_to_version[project_name]

    packages = self.__project_to_packages[project_name].copy()
    for package in packages:
      self.remove_package(package)
    del self.__project_to_packages[project_name]

    logging.info('Removed project: {}'.format(project_name))


  def unmark_project_as_dirty(self, project_name):
    assert self.__project_exists(project_name)
    self.__project_to_dirty[project_name] = False
    logging.debug('Unmarked project as dirty: {}'.format(project_name))


  def update(self, change):
    if isinstance(change, changelog.AddPackage):
      package = os.path.join(nouns.PACKAGES_DIRECTORY, change.name)
      project_name = self.get_project_name_from_package(package)

      # Create the project if it does not already exist.
      if not self.__project_exists(project_name):
        logging.warn('Created non-existent project {} '\
                     'for added package {}'.format(project_name, package))
        self.add_project(project_name)
      else:
        # Add the package if it still exists on disk.
        if os.path.exists(package):
          self.add_package(package)
          self.inc_project_version(project_name)
        else:
          logging.warn('Did not add non-existent package {}'.format(package))

    elif isinstance(change, changelog.AddProject):
      self.__add_project_and_packages(change.name)

    elif isinstance(change, changelog.RemovePackage):
      packages = os.path.join(nouns.PACKAGES_DIRECTORY, change.name)
      project_name = self.get_project_name_from_package(packages)

      # Remove the package only if the project itself still exists.
      if self.__project_exists(project_name):
        for package in sorted(glob.glob(packages)):
          if self.__package_exists(package):
            self.remove_package(package)
            self.inc_project_version(project_name)
          else:
            logging.warn('Could not remove non-existent package {} '\
                         'from project {}'.format(package, project_name))
      else:
        logging.warn('Could not remove packages {} '\
                     'for non-existent project {}'.format(packages,
                                                          project_name))

    else:
      assert isinstance(change, changelog.RemoveProject)
      project_name = change.name

      # Remove the project only if the project itself still exists.
      if self.__project_exists(project_name):
        self.remove_project(project_name)
      else:
        logging.warn('Could not remove '\
                     'non-existent project {}'.format(project_name))
