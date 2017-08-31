#!/usr/bin/env python3


# 1st-party
import datetime
import logging
import os


# 2nd-party
from metadatawriter import MetadataWriter, write
from nouns import MERCURY_NOHASH_DIRECTORY,
                  MERCURY_NOHASH_DIRTY_PROJECTS_CACHE_FILEPATH, \
                  MERCURY_NOHASH_METADATA_PATCH_LENGTH_CACHE_FILEPATH, \
                  MERCURY_NOHASH_METADATA_DIRECTORY
from repository import MercuryAlphabeticalRepository


class MercuryMetadataWriter(MetadataWriter):


  def make_snapshot_administrator_metadata(self, timestamp):
    if len(self.repository.projects.dirty) > 0:
      meta = {}

      # project developers
      for project_name in self.repository.projects.names:
        # TODO: Really should not be hardcoding file paths. Instead, each
        # metadata object should know where it lives on disk.
        filename = 'packages/{}.json'.format(project_name)
        meta[filename] = \
                    self.repository.projects.get_project_version(project_name)

      # Commit the snapshot metadata to memory.
      keyids = self.repository.snapshot_administrator_keyids
      version = self.repository.snapshot_administrator_version
      self.snapshot_administrator_metadata = \
                            self.make_release_metadata(keyids=keyids,
                                                       meta=meta,
                                                       timestamp=timestamp,
                                                       version=version)
      self.snapshot_administrator_metadata_json = \
                    self.jsonify(self.snapshot_administrator_metadata)

    else:
      logging.debug('No new snapshot metadata, '\
                    'because no new package metadata.')


  def project_metadata_identifier(self, project_name):
    return self.repository.projects.get_project_version(project_name)


if __name__ == '__main__':
  log_filename = os.path.join(MERCURY_NOHASH_METADATA_DIRECTORY,
                              'write-mercury-nohash-metadata.log')
  write(log_filename, MERCURY_NOHASH_DIRTY_PROJECTS_CACHE_FILEPATH,
        MERCURY_NOHASH_METADATA_PATCH_LENGTH_CACHE_FILEPATH,
        MercuryAlphabeticalRepository, MercuryMetadataWriter,
        MERCURY_NOHASH_DIRECTORY)
