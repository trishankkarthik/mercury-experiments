#!/usr/bin/env python3


# 1st-party
import json
import logging


# 2nd-party
from metadatareader import MetadataReader, PackageCost, UnknownPackage, \
                           UnknownProject, read
from nouns import METADATA_DIRECTORY, \
                  TUF_COST_FOR_NEW_USERS_FILEPATH, \
                  TUF_DIRECTORY, \
                  TUF_DIRTY_PROJECTS_CACHE_FILEPATH, \
                  TUF_VERSION_BEST_LOG_FILENAME, \
                  TUF_METADATA_PATCH_LENGTH_CACHE_FILEPATH, \
                  TUF_VERSION_BEST_OUTPUT_FILENAME
from projects import Projects


class TUFMetadataReader(MetadataReader):


  def __init__(self, ip_address):
    super().__init__(ip_address)

    # NOTE: Assume everyone starts with a complete copy of first snapshot +
    # project metadata. In our implementation, this simply means that everyone
    # must know first snapshot metadata relpath.
    self._prev_snapshot_metadata_relpath = 'snapshot.1395359999.json'

    self.__dirty_projects = {}


  # Add to the baseline the cost of fetching every other project metadata.
  # Which projects have new metadata in the current snapshot metadata?
  # FIXME: Compress all dirty project metadata files in one shot.
  def __extra_charge(self, package_cost):
    logging.debug('Fetching {:,} DIRTY projects!'\
                  .format(len(self.__dirty_projects)))
    if len(self.__dirty_projects) == 0:
      assert self._prev_prev_snapshot_metadata_relpath == \
             self._prev_snapshot_metadata_relpath,\
             'prev != curr snapshot, but there are no dirty projects!'

    for project_metadata_relpath, \
        project_metadata_identifier in self.__dirty_projects.items():
      assert project_metadata_relpath.startswith('packages/')
      assert project_metadata_relpath.endswith('.json')
      project_name = project_metadata_relpath[9:-5]

      prev_project_metadata_relpath = \
              self._get_prev_project_metadata_relpath(project_metadata_relpath,
                                                      project_name)
      # NOTE: Hint to download the project version metadata file.
      if prev_project_metadata_relpath:
        prev_project_metadata_relpath += '.version'

      curr_project_metadata_relpath = 'packages/{}.{}.json'\
                                      .format(project_name,
                                              project_metadata_identifier)
      # NOTE: Hint to download the project version metadata file.
      curr_project_metadata_relpath += '.version'

      logging.debug('Prev, curr project = {}, {}'\
                    .format(prev_project_metadata_relpath,
                            curr_project_metadata_relpath))

      # 3. Fetch every other project metadata, if not already cached,
      # according to the latest snapshot metadata.
      project_metadata_length = \
                self.get_cached_metadata_cost(prev_project_metadata_relpath,
                                              curr_project_metadata_relpath)
      logging.debug('Project metadata length = {:,}'\
                    .format(project_metadata_length))
      package_cost.add_project_metadata_length(project_metadata_length)

    logging.debug('Package cost = {}'.format(package_cost))
    return package_cost


  def _get_prev_project_metadata_relpath(self, project_metadata_relpath,
                                         project_name):
    # If we are here, we are a returning user who has already calculated the
    # baseline cost, and thus we have the set the previous snapshot metadata
    # relpath to the current snapshot metadata relpath. Thus, we want the
    # previous snapshot metadata relpath before the previous snapshot metadata
    # relpath.
    prev_snapshot_metadata_relpath = self._prev_prev_snapshot_metadata_relpath
    prev_snapshot_metadata = \
                        self._read_snapshot(prev_snapshot_metadata_relpath)

    # NOTE: This computation would be stupid for Mercury, because it would
    # just be packages/project.1.json anyway, except for one thing: the
    # project itself could be missing in the previous snapshot.
    if project_metadata_relpath in prev_snapshot_metadata:
      prev_project_metadata_identifier = \
                      prev_snapshot_metadata.get(project_metadata_relpath)
      prev_project_metadata_relpath = \
            'packages/{}.{}.json'.format(project_name,
                                         prev_project_metadata_identifier)
    # Project did not exist in previous snapshot!
    else:
      prev_project_metadata_relpath = None

    return prev_project_metadata_relpath


  def _load_dirty_projects(self, curr_metadata_relpath, key):
    if curr_metadata_relpath.startswith('snapshot.'):
      self.__dirty_projects = self._DIRTY_PROJECTS_CACHE[key]
      logging.debug('LOAD DIRTY')


  @classmethod
  def _read_metadata(cls, metadata_relpath):
    # NOTE: Hint to download the project version metadata file.
    if metadata_relpath.endswith('.version'):
      real_metadata_relpath = metadata_relpath[:-8]
      assert real_metadata_relpath.startswith('packages/')
      assert real_metadata_relpath.endswith('.json')
      real_metadata = super()._read_metadata(real_metadata_relpath)

      # NOTE: Approximate the project version metadata file (i.e., a version
      # of the project metadata file that contains only the version number of
      # the actual project metadata file) by deleting everything but the version
      # number from the signed part of the message. The signatures will remain
      # the same; this is okay.
      return {
        'signatures': real_metadata['signatures'],
        'signed': {
          'version': real_metadata['signed']['version']
        }
      }

    else:
      return super()._read_metadata(metadata_relpath)


  def _reset_dirty_projects(self, curr_metadata_relpath):
    if curr_metadata_relpath.startswith('snapshot.'):
      self.__dirty_projects = {}
      logging.debug('RESET DIRTY')


  def _store_dirty_projects(self, curr_metadata_relpath, key, patch):
    if curr_metadata_relpath.startswith('snapshot.'):
      dirty_projects = self._get_dirty_projects(patch)
      self._DIRTY_PROJECTS_CACHE[key] = dirty_projects
      self.__dirty_projects = dirty_projects
      logging.debug('STORE DIRTY')


  def new_charge(self, curr_snapshot_timestamp, url):
      package_cost = self._baseline_charge(curr_snapshot_timestamp, url)
      return self.__extra_charge(package_cost)


  def return_charge(self, curr_snapshot_timestamp, url):
      package_cost = self._baseline_charge(curr_snapshot_timestamp, url)
      return self.__extra_charge(package_cost)


if __name__ == '__main__':
  read(TUF_VERSION_BEST_LOG_FILENAME, TUFMetadataReader, TUF_DIRECTORY,
       TUF_METADATA_PATCH_LENGTH_CACHE_FILEPATH,
       TUF_DIRTY_PROJECTS_CACHE_FILEPATH, TUF_VERSION_BEST_OUTPUT_FILENAME)
