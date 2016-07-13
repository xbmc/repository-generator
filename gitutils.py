# -*- coding: utf-8 -*-
#
#     Copyright (C) 2015 Team Kodi
#     http://kodi.tv
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import git
import logging
import os
import shutil
import tempfile
import zipfile
from distutils.version import LooseVersion
from io import BytesIO
from itertools import groupby
from xml.etree import ElementTree as ET
from artifacts import Artifact, pack_artifact


logger = logging.getLogger(__name__)


def makedirs(path):
    try:
        os.makedirs(path)
    except OSError:
        pass


def meets_version_requirements(imports, min_versions):
    for addon_id, imported_version in imports:
        if addon_id in min_versions:
            if imported_version < min_versions[addon_id]:
                return False
    return True


def collect_artifacts(git_repos, refs, min_versions):
    for repo_path in git_repos:
        repo = git.Repo(repo_path)
        if repo.bare:
            logger.warning("Repo %s is bare, Skipping", repo_path)
            continue
        for ref in refs:
            if ref not in repo.refs:
                logger.warning("No such ref %s in repo %s. Skipping.", ref, repo_path)
                continue
            for directory in repo.refs[ref].commit.tree.trees:
                try:
                    addon_xml = directory['addon.xml'].data_stream.read()
                    tree = ET.fromstring(addon_xml)
                    artifact_id = directory.name.encode('utf-8')
                    version = tree.attrib['version'].encode('utf-8')

                    imports = [(elem.attrib['addon'], LooseVersion(elem.attrib.get('version', '0.0.0')))
                               for elem in tree.findall('./requires/import')]
                    if meets_version_requirements(imports, min_versions):
                        yield Artifact(artifact_id, version, repo_path, ref + ":" + artifact_id)
                except (ET.ParseError, KeyError, IndexError) as e:
                    logger.exception("Failed to read addon data from directory '%s'" % directory.name.encode('utf-8'))


def filter_latest_version(artifacts):
    artifacts = list(artifacts)
    artifacts.sort(key=lambda _: _.addon_id)
    for addon_id, versions in groupby(artifacts, key=lambda _: _.addon_id):
        versions = list(versions)
        versions.sort(key=lambda _: LooseVersion(_.version), reverse=True)
        if len(versions) >= 2 and versions[0].version == versions[1].version:
            logger.warning("Duplicate artifact. I will pick one at random. First: %r. Second: %r", versions[0], versions[1])
        yield versions[0]


def delete_old_artifacts(target_dir, versions_to_keep):
    for artifact_id in os.listdir(target_dir):
        artifact_dir = os.path.join(target_dir, artifact_id)
        if not os.path.isdir(artifact_dir):
            continue

        zips = [name for name in os.listdir(artifact_dir) if os.path.splitext(name)[1] == '.zip']
        if len(zips) <= versions_to_keep:
            continue

        version_from_name = lambda name: os.path.splitext(name)[0].rsplit('-', 1)[1]
        zips.sort(key=lambda _: LooseVersion(version_from_name(_)), reverse=True)

        for filename in zips[versions_to_keep:]:
            logger.debug("Removing old artifact %s", filename)
            os.remove(os.path.join(artifact_dir, filename))

            changelog = os.path.join(artifact_dir, 'changelog-%s.txt' % version_from_name(filename))
            if os.path.exists(changelog):
                os.remove(changelog)


def write_artifact(artifact, outdir):
    """ Reads artifact data from git and writes a zip file (and companion files) to `outdir` """
    working_dir = tempfile.mkdtemp()
    repo = git.Repo(artifact.git_repo)

    # Extract files to working_dir
    buffer = BytesIO()
    repo.archive(buffer, artifact.treeish, format="zip")
    with zipfile.ZipFile(buffer, 'r') as zf:
        zf.extractall(working_dir)

    pack_artifact(artifact, working_dir, outdir)
    shutil.rmtree(working_dir)


def update_changed_artifacts(git_repos, refs, min_versions, outdir):
    """ Returns a tuple with number of new and deleted artifacts. """
    artifacts = collect_artifacts(git_repos, refs, min_versions)
    artifacts = list(filter_latest_version(artifacts))

    added = [a for a in artifacts if not os.path.exists(
        os.path.join(outdir, a.addon_id, "%s-%s.zip" % (a.addon_id, a.version)))]
    current = set([name for name in os.listdir(outdir)
                   if os.path.isdir(os.path.join(outdir, name)) and not name.startswith('.')])
    removed = current - set([_.addon_id for _ in artifacts])

    for artifact in added:
        logger.debug("New artifact %s version %s", artifact.addon_id, artifact.version)
        dest = os.path.join(outdir, artifact.addon_id)
        makedirs(dest)
        delete_companion_files(dest)
        write_artifact(artifact, dest)

    for artifact_id in removed:
        logger.debug("Removing artifact %s", artifact_id)
        shutil.rmtree(os.path.join(outdir, artifact_id))

    return len(added), len(removed)


def delete_companion_files(path):
    for name in os.listdir(path):
        if os.path.splitext(name)[1] != '.zip':
            try:
                if os.path.isdir(os.path.join(path, name)):
                    shutil.rmtree(os.path.join(path, name))
                else:
                    os.remove(os.path.join(path, name))
            except (IOError, OSError) as ex:
                logger.warning("Failed to remove companion file '%s'" % os.path.join(path, name))
                logger.exception(ex)
