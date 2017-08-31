#!/usr/bin/env python3


# 2nd-party
from metadatareader import MetadataReader, read
from nouns import MERCURY_DIRECTORY, \
                  MERCURY_DIRTY_PROJECTS_CACHE_FILEPATH, \
                  MERCURY_BEST_LOG_FILENAME, \
                  MERCURY_METADATA_PATCH_LENGTH_CACHE_FILEPATH, \
                  MERCURY_BEST_OUTPUT_FILENAME


class MercuryMetadataReader(MetadataReader):


  def __init__(self, ip_address):
    super().__init__(ip_address)

    # NOTE: Assume everyone starts with a complete copy of first snapshot +
    # project metadata.
    self._prev_snapshot_metadata_relpath = self.__PREV_SNAPSHOT_METADATA_RELPATH
    # NOTE: Every user will likely download different versions of the same
    # project metadata files.
    self.__prev_project_metadata_relpath = {}


  def _get_prev_project_metadata_relpath(self, project_metadata_relpath,
                                         project_name):
    # Has the user downloaded a newer version of this project metadata file?
    prev_project_metadata_relpath = \
              self.__prev_project_metadata_relpath.get(project_metadata_relpath)

    # If not, then consult the first snapshot.
    if not prev_project_metadata_relpath:
      prev_project_metadata_relpath = \
              self.__PREV_PROJECT_METADATA_RELPATH.get(project_metadata_relpath)

    return prev_project_metadata_relpath


  def _set_prev_project_metadata_relpath(self, project_metadata_relpath,
                                         curr_project_metadata_relpath):
    self.__prev_project_metadata_relpath[project_metadata_relpath] = \
                                                  curr_project_metadata_relpath


  def new_charge(self, curr_snapshot_timestamp, url):
    return self._baseline_charge(curr_snapshot_timestamp, url)


  def return_charge(self, curr_snapshot_timestamp, url):
    return self._baseline_charge(curr_snapshot_timestamp, url)


  @classmethod
  def setup(cls, metadata_directory, metadata_patch_length_cache_filepath,
            dirty_projects_cache_filepath):
    super().setup(metadata_directory, metadata_patch_length_cache_filepath,
                  dirty_projects_cache_filepath)

    # NOTE: Assume everyone starts with a complete copy of first snapshot +
    # project metadata. In our implementation, this simply means that everyone
    # must know every project metadata relpath from the first snapshot.
    cls.__PREV_SNAPSHOT_METADATA_RELPATH = 'snapshot.1395359999.json'
    snapshot_metadata = cls._read_snapshot(cls.__PREV_SNAPSHOT_METADATA_RELPATH)
    cls.__PREV_PROJECT_METADATA_RELPATH = {}

    for project_metadata_relpath in snapshot_metadata:
      project_metadata_identifier = \
                 cls._get_project_metadata_identifier(snapshot_metadata[\
                                                      project_metadata_relpath])
      assert project_metadata_relpath.endswith('.json')
      prev_project_metadata_relpath = \
        '{}{}.{}'.format(project_metadata_relpath[:-4],
                         project_metadata_identifier,
                         project_metadata_relpath[-4:])
      cls.__PREV_PROJECT_METADATA_RELPATH[project_metadata_relpath] = \
                                                  prev_project_metadata_relpath


if __name__ == '__main__':
  read(MERCURY_BEST_LOG_FILENAME,
       MercuryMetadataReader,
       MERCURY_DIRECTORY,
       MERCURY_METADATA_PATCH_LENGTH_CACHE_FILEPATH,
       MERCURY_DIRTY_PROJECTS_CACHE_FILEPATH,
       MERCURY_BEST_OUTPUT_FILENAME)
