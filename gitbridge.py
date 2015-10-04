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

import os
import shutil
import logging
import subprocess
import tempfile
import zipfile
import git
from distutils.version import LooseVersion
from xml.etree import ElementTree as ET
from collections import namedtuple
from io import BytesIO
from itertools import groupby


logger = logging.getLogger(__name__)

Artifact = namedtuple('Artifact', ['addon_id', 'version', 'git_repo', 'treeish'])


def makedirs(path):
    try:
        os.makedirs(path)
    except OSError:
        pass


def pack_textures(working_dir):
    tree = ET.parse(os.path.join(working_dir, 'addon.xml'))
    is_skin = tree.find("./extension[@point='xbmc.gui.skin']") is not None
    compile_imagepack = tree.find("./extension[@compile='true']") is not None

    if is_skin:
        invoke_texturepacker(os.path.join(working_dir, 'media'),
                os.path.join(working_dir, 'media', 'Textures.xbt'))

        if os.path.exists(os.path.join(working_dir, 'themes')):
            for theme_name in os.listdir(os.path.join(working_dir, 'themes')):
                invoke_texturepacker(os.path.join(working_dir, 'themes', theme_name),
                        os.path.join(working_dir, 'themes', theme_name + '.xbt'))

        _remove_non_xbt_files(os.path.join(working_dir, 'media'))
        _remove_non_xbt_files(os.path.join(working_dir, 'themes'))

    if compile_imagepack:
        invoke_texturepacker(os.path.join(working_dir, 'resources'),
                os.path.join(working_dir, 'resources', 'Textures.xbt'))
        _remove_non_xbt_files(os.path.join(working_dir, 'resources'))


def _remove_non_xbt_files(directory):
    for root, dirs, files in os.walk(directory, topdown=False):
        for name in files:
            if not name.endswith(".xbt"):
                os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))


def invoke_texturepacker(input, output):
    logger.debug("Running texturepacker on %s", input)
    cmd = ['TexturePacker', '-dupecheck', '-input', input, '-output', output]
    with open(os.devnull, 'w') as f:
        subprocess.check_call(cmd, stdout=f, stderr=f)


def write_artifact(artifact, outdir):
    repo = git.Repo(artifact.git_repo)
    working_dir = tempfile.mkdtemp()
    makedirs(outdir)

    # Extract artifact files from git into working_dir
    buffer = BytesIO()
    repo.archive(buffer, artifact.treeish, format="zip")
    with zipfile.ZipFile(buffer, 'r') as zf:
        zf.extractall(working_dir)

    pack_textures(working_dir)
    if os.path.exists(os.path.join(working_dir, '_screenshots')):
        shutil.rmtree(os.path.join(working_dir, '_screenshots'))

    # Write and compress files in working_dir to the final zip file
    dest_file = os.path.join(outdir, "%s-%s.zip" % (artifact.addon_id, artifact.version))
    with zipfile.ZipFile(dest_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(working_dir):
            for name in files:
                local_path = os.path.join(root, name)
                arc_path = artifact.addon_id + '/' + os.path.relpath(local_path, start=working_dir)
                zf.write(local_path, arc_path)

    # Copy extra files
    if os.path.exists(os.path.join(working_dir, "icon.png")):
        shutil.copyfile(os.path.join(working_dir, "icon.png"), os.path.join(outdir, "icon.png"))

    if os.path.exists(os.path.join(working_dir, "fanart.jpg")):
        shutil.copyfile(os.path.join(working_dir, "fanart.jpg"), os.path.join(outdir, "fanart.jpg"))

    if os.path.exists(os.path.join(working_dir, "changelog.txt")):
        shutil.copyfile(os.path.join(working_dir, "changelog.txt"), os.path.join(outdir, "changelog-%s.txt" % artifact.version))

    # Cleanup
    shutil.rmtree(working_dir)


def purge_old_artifacts(outdir, versions_to_keep):
    for artifact_id in os.listdir(outdir):
        artifact_dir = os.path.join(outdir, artifact_id)
        zips = [name for name in os.listdir(artifact_dir) if os.path.splitext(name)[1] == '.zip']
        if len(zips) <= versions_to_keep:
            return

        version_from_name = lambda name: os.path.splitext(name)[0].rsplit('-', 1)[1]
        zips.sort(key=lambda _: LooseVersion(version_from_name(_)), reverse=True)

        for filename in zips[versions_to_keep:]:
            logger.info("removing old artifact '%s'", filename)
            os.remove(os.path.join(artifact_dir, filename))

            changelog = os.path.join(artifact_dir, 'changelog-%s.txt' % version_from_name(filename))
            if os.path.exists(changelog):
                os.remove(changelog)


def collect_artifacts(git_repos, refs):
    artifacts = []
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
                artifacts.append(Artifact(
                    directory.name.encode('utf-8'),
                    tree.attrib['version'].encode('utf-8'),
                    repo_path,
                    ref + ":" + directory.name.encode('utf-8')))

    # Return only the latest version
    artifacts.sort(key=lambda _: _.addon_id)
    for addon_id, versions in groupby(artifacts, key=lambda _: _.addon_id):
        versions = list(versions)
        versions.sort(key=lambda _: LooseVersion(_.version), reverse=True)
        if len(versions) >= 2 and versions[0].version == versions[1].version:
            logger.warn("Duplicate artifact. I will pick one at random. First: %r. Second: %r", versions[0], versions[1])
        yield versions[0]


def update_changed_artifacts(git_repos, refs, outdir):
    artifacts = list(collect_artifacts(git_repos, refs))

    added = [a for a in artifacts if not os.path.exists(
        os.path.join(outdir, a.addon_id, "%s-%s.zip" % (a.addon_id, a.version)))]
    current = set([name for name in os.listdir(outdir) if os.path.isdir(os.path.join(outdir, name))])
    removed = current - set([_.addon_id for _ in artifacts])

    if len(added) == 0 and len(removed) == 0:
        logger.info("No changes")
        return

    for artifact in added:
        logger.debug("New artifact '%s' version %s", artifact.addon_id, artifact.version)
        makedirs(os.path.join(outdir, artifact.addon_id))
        write_artifact(artifact, os.path.join(outdir, artifact.addon_id))

    for artifact_id in removed:
        logger.debug("Artifact with id '%s' removed", artifact_id)
        shutil.rmtree(os.path.join(outdir, artifact_id))
