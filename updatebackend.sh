#!/bin/bash
REPO=/var/www/addons

touch /tmp/scriptran
cd $REPO

OLDREV=`git show-ref -s origin/master`
git fetch
NEWREV=`git show-ref -s origin/master`
if [ "${NEWREV}" != "${OLDREV}" ]; then
  git reset --hard origin/master
  git clean -xfd
fi
exit 0
