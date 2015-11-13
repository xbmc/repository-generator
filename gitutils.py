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
            logger.warn("Repo '%s' is bare, Skipping", repo_path)
            continue
        for ref in refs:
            if ref not in repo.refs:
                logger.warn("No such ref '%s' in repo '%s'. Skipping.", ref, repo_path)
                continue
            for directory in repo.refs[ref].commit.tree.trees:
                addon_xml = directory['addon.xml'].data_stream.read()
                tree = ET.fromstring(addon_xml)
                artifact_id = directory.name.encode('utf-8')

                # check dependencies
                imports = [(elem.attrib['addon'], LooseVersion(elem.attrib.get('version', '0.0.0')))
                           for elem in tree.findall('./requires/import')]
                if not meets_version_requirements(imports, min_versions):
                    logging.debug("Skipping artifact %s unmet dependencies.", artifact_id)
                    continue

                yield Artifact(artifact_id, tree.attrib['version'].encode('utf-8'),
                               repo_path, ref + ":" + directory.name.encode('utf-8'))


def filter_latest_version(artifacts):
    artifacts = list(artifacts)
    artifacts.sort(key=lambda _: _.addon_id)
    for addon_id, versions in groupby(artifacts, key=lambda _: _.addon_id):
        versions = list(versions)
        versions.sort(key=lambda _: LooseVersion(_.version), reverse=True)
        if len(versions) >= 2 and versions[0].version == versions[1].version:
            logger.warn("Duplicate artifact. I will pick one at random. First: %r. Second: %r", versions[0], versions[1])
        yield versions[0]


def delete_old_artifacts(artifact_dir, versions_to_keep):
    for artifact_id in os.listdir(artifact_dir):
        artifact_dir = os.path.join(artifact_dir, artifact_id)
        zips = [name for name in os.listdir(artifact_dir) if os.path.splitext(name)[1] == '.zip']
        if len(zips) <= versions_to_keep:
            return

        version_from_name = lambda name: os.path.splitext(name)[0].rsplit('-', 1)[1]
        zips.sort(key=lambda _: LooseVersion(version_from_name(_)), reverse=True)

        for filename in zips[versions_to_keep:]:
            logger.info("Removing old artifact '%s'", filename)
            os.remove(os.path.join(artifact_dir, filename))

            changelog = os.path.join(artifact_dir, 'changelog-%s.txt' % version_from_name(filename))
            if os.path.exists(changelog):
                os.remove(changelog)


def write_artifact(artifact, outdir):
    """ Reads artifact data from git and writes a zip file (and companion file) to `outdir` """
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
    artifacts = collect_artifacts(git_repos, refs, min_versions)
    artifacts = list(filter_latest_version(artifacts))

    added = [a for a in artifacts if not os.path.exists(
        os.path.join(outdir, a.addon_id, "%s-%s.zip" % (a.addon_id, a.version)))]
    current = set([name for name in os.listdir(outdir) if os.path.isdir(os.path.join(outdir, name))])
    removed = current - set([_.addon_id for _ in artifacts])

    if len(added) == 0 and len(removed) == 0:
        logger.info("No changes")
        return

    for artifact in added:
        dest = os.path.join(outdir, artifact.addon_id)
        makedirs(dest)
        write_artifact(artifact, dest)
        logger.info("Added artifact '%s' version %s", artifact.addon_id, artifact.version)

    for artifact_id in removed:
        shutil.rmtree(os.path.join(outdir, artifact_id))
        logger.info("Removed  artifact '%s'", artifact_id)
