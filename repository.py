

# 1st-party
import logging


# 2nd-party
from metadatawriter import MetadataWriter
from projects import Projects


class Repository:


  '''Keep state on the repository, e.g. keys, projects (their keys and
  packages), delegations of projects.'''


  def __init__(self, changelog_reader):
    # Administrator keyids.
    # Return a *deterministic* "keyid" for the snapshot administrator.
    # WARNING: Do *NOT* reuse this value anywhere else!
    # It just so happens that a SHA-256 hex digest is as long as our keyid.
    self.__snapshot_administrator_keyid = \
                          MetadataWriter.get_sha256('snapshot'.encode('utf-8'))
    self.__projects_administrator_keyid = MetadataWriter.get_random_keyid()
    self.__projects_subordinates_keyid = self.__projects_administrator_keyid

    # Administrator keyvals.
    self.__keyid_to_keyval = {
      self.__snapshot_administrator_keyid:
                                    MetadataWriter.get_random_ed25519_keyval(),
      self.__projects_administrator_keyid:
                                    MetadataWriter.get_random_ed25519_keyval()
    }

    # Administrator versions.
    self.__snapshot_administrator_version = 0
    self.__projects_administrator_version = 0

    # A map of which projects subordinates are responsible for which projects.
    # str (role name): {str} (set of project names)
    self._projects_subordinates_to_projects = {}
    # str (role name): int (version number > 0)
    self._projects_subordinates_to_version = {}

    # This object takes care of projects and their packages, keys, etc.
    self.__projects = Projects(changelog_reader)

    # Custom setup routine here.
    self._setup()


  def get_projects_subordinate_version(self, projects_subordinate):
    assert self._projects_subordinates_to_projects.keys() == \
           self._projects_subordinates_to_version.keys()
    assert projects_subordinate in self._projects_subordinates_to_version

    return self._projects_subordinates_to_version[projects_subordinate]


  def inc_projects_administrator_version(self):
    self.__projects_administrator_version += 1


  def inc_projects_subordinate_version(self, projects_subordinate):
    assert self._projects_subordinates_to_projects.keys() == \
           self._projects_subordinates_to_version.keys()
    assert projects_subordinate in self._projects_subordinates_to_version

    self._projects_subordinates_to_version[projects_subordinate] += 1


  def inc_snapshot_administrator_version(self):
    self.__snapshot_administrator_version += 1


  @property
  def keyid_to_keyval(self):
    return self.__keyid_to_keyval.copy()


  @property
  def projects(self):
    return self.__projects


  @property
  def projects_administrator_keyids(self):
    return (self.__projects_administrator_keyid,)


  @property
  def projects_administrator_version(self):
    assert self.__projects_administrator_version > 0
    return self.__projects_administrator_version


  @property
  def projects_subordinates(self):
    return sorted(self.projects_subordinates_to_projects.keys())


  @property
  def projects_subordinates_keyids(self):
    return (self.__projects_subordinates_keyid,)


  @property
  def projects_subordinates_to_keyids(self):
    assert self._projects_subordinates_to_projects.keys() == \
           self._projects_subordinates_to_version.keys()

    return {
      role: self.projects_subordinates_keyids \
                            for role in self._projects_subordinates_to_projects
    }


  @property
  def projects_subordinates_to_projects(self):
    assert self._projects_subordinates_to_projects.keys() == \
           self._projects_subordinates_to_version.keys()
    # TODO: assert that projects are mutex between subordinates

    return self._projects_subordinates_to_projects.copy()


  def release(self):
    if len(self.projects.dirty) > 0:
      #self.inc_projects_administrator_version()
      self.inc_snapshot_administrator_version()

    else:
      logging.debug('No repository release, '\
                    'because there is no dirty project metadata.')


  def _setup(self):
    raise NotImplementedError()


  @property
  def snapshot_administrator_keyids(self):
    return (self.__snapshot_administrator_keyid,)


  @property
  def snapshot_administrator_version(self):
    assert self.__snapshot_administrator_version > 0
    return self.__snapshot_administrator_version


  def update(self, change):
    self.__projects.update(change)


class TUFAlphabeticalRepository(Repository):


  def _setup(self):
    for project_name in self.projects.names:
      role = project_name[0]
      projects = self._projects_subordinates_to_projects.setdefault(role,
                                                                    set())
      projects.add(project_name)
      self._projects_subordinates_to_version[role] = 1


class MercuryAlphabeticalRepository(TUFAlphabeticalRepository): pass
