SHELL := /bin/bash

deploy:
#	cp db.sqlite3 /tmp/db.sqlite3
	# git checkout heroku
	# git merge master -m "Merge master"
	# cp /tmp/db.sqlite3 .
	# git add -f db.sqlite3
	# git commit db.sqlite3 -m "Add DB" --allow-empty
	git push heroku master
	# git rm --cached db.sqlite3
	# git checkout master
	# cp /tmp/db.sqlite3 .
