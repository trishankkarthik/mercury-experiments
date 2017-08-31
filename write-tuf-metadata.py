#!/usr/bin/env python3


# 1st-party
import logging
import os


# 2nd-party
from metadatawriter import MetadataWriter, write
from nouns import METADATA_DIRECTORY, TUF_DIRECTORY, \
                  TUF_DIRTY_PROJECTS_CACHE_FILEPATH, \
                  TUF_METADATA_PATCH_LENGTH_CACHE_FILEPATH
from repository import TUFAlphabeticalRepository


class TUFMetadataWriter(MetadataWriter):


  def make_snapshot_administrator_metadata(self, timestamp):
    if len(self.repository.projects.dirty) > 0:
      meta = {}

      # project developers
      for project_name in self.repository.projects.names:
        # TODO: Really should not be hardcoding file paths. Instead, each
        # metadata object should know where it lives on disk.
        filename = 'packages/{}.json'.format(project_name)
        meta[filename] = \
            self.get_sha256(self.project_developer_metadata_json[project_name])

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
    return self.get_sha256(self.project_developer_metadata_json[project_name])


if __name__ == '__main__':
  log_filename = os.path.join(METADATA_DIRECTORY, 'write-tuf-metadata.log')
  write(log_filename, TUF_DIRTY_PROJECTS_CACHE_FILEPATH,
        TUF_METADATA_PATCH_LENGTH_CACHE_FILEPATH, TUFAlphabeticalRepository,
        TUFMetadataWriter, TUF_DIRECTORY)
