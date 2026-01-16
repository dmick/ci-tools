# A grab-bag of useful tools for stuff in the sepia lab

Note: the tools that access jenkins need python-jenkins installed.
Since I tend to do things like this with my own $HOME/v virtualenv,
sometimes I'm lazy and just set the interpreter path 
to /home/dmick/v/bin/python3.  Python packaging is frustrating.

- **compare.py**: look up Jenkins node labels by running jenkins.tags
(also in this repo) and compare the output to the local Ansible 
inventory files.  For maintaining the jenkins node labels with Ansible. 

- **jenkins-tags.py**: look up Jenkins node labels.  Takes a bunch of
different arguments for limiting output.  Also has a mode '-l' that will
generate a comma-separated list useful for things like pdsh -w $(jenkins-tags -l-t arm64) <cmd>, or you can change the delimiter.  Will also output a form useful for including in ansible inventory.  Note the offline options.

- **jobinfo.py**: Look up a jenkins job by name RE; show all cached builds,
newest to oldest.  Limit how many with -c, output json if you want to
further query, etc.  Also gets a list of all jobnames.  WIP.

- **nodestatus.py**: Show current status of all jenkins nodes; if running a
build, show some info about the build; if offline, try to show who and why.
WIP.

  **maasapi.py**: call the MaaS API; handles the OAuth authentication, allows get/put/post/delete operations
