#!/usr/bin/env python3


# 2nd-party
from metadatareader import MetadataReader, read
from nouns import MERCURY_NOHASH_DIRECTORY, \
                  MERCURY_NOHASH_DIRTY_PROJECTS_CACHE_FILEPATH, \
                  MERCURY_NOHASH_WORST_LOG_FILENAME, \
                  MERCURY_NOHASH_METADATA_PATCH_LENGTH_CACHE_FILEPATH, \
                  MERCURY_NOHASH_WORST_OUTPUT_FILENAME


class MercuryNoHashMetadataReader(MetadataReader):


  def __init__(self, ip_address):
    super().__init__(ip_address)

    self.__prev_project_metadata_relpath = {}


  def _get_prev_project_metadata_relpath(self, project_metadata_relpath,
                                         project_name):
    return self.__prev_project_metadata_relpath.get(project_metadata_relpath)


  def _set_prev_project_metadata_relpath(self, project_metadata_relpath,
                                         curr_project_metadata_relpath):
    self.__prev_project_metadata_relpath[project_metadata_relpath] = \
                                                  curr_project_metadata_relpath


  def new_charge(self, curr_snapshot_timestamp, url):
    return self._baseline_charge(curr_snapshot_timestamp, url)


  def return_charge(self, curr_snapshot_timestamp, url):
    return self._baseline_charge(curr_snapshot_timestamp, url)


if __name__ == '__main__':
  read(MERCURY_NOHASH_WORST_LOG_FILENAME,
       MercuryNoHashMetadataReader,
       MERCURY_NOHASH_DIRECTORY,
       MERCURY_NOHASH_METADATA_PATCH_LENGTH_CACHE_FILEPATH,
       MERCURY_NOHASH_DIRTY_PROJECTS_CACHE_FILEPATH,
       MERCURY_NOHASH_WORST_OUTPUT_FILENAME)
