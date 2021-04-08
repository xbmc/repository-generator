#!/bin/bash
echo "=================================================================="
echo "$(date -Ins) Repository update started"
echo "$(date -Ins) - Running updaterepo.py"
./updaterepo.py || exit 1
echo "$(date -Ins) - Running update_indexes.py"
./update_indexes.py
index_status=$?
if [ -f mirrorsync.sh ]; then
	if [ $index_status -eq 64 ]; then
		echo "$(date -Ins) - No index files changed, skipping mirror sync"
	elif [ $index_status -eq 0 ]; then
		echo "$(date -Ins) - Triggering mirror sync"
		./mirrorsync.sh || exit 1
	else
		exit 1
	fi
fi
echo "$(date -Ins) Repository update finished"
