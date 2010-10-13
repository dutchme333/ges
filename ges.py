#!/usr/bin/env python
'''
Copyright (c) 2010  Daniel Dotsenko <dotsa (a) hotmail com>

This file is part of ges Project.

ges Project is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 2 of the License, or
(at your option) any later version.

ges Project is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with ges Project.  If not, see <http://www.gnu.org/licenses/>.
'''
import io
import os
import sys

path = os.path.abspath('.')

sys.path.append(os.path.join(path, 'git_http_backend'))
sys.path.append(os.path.join(path, 'gitpython', 'lib'))

import git_http_backend
from cherrypy import wsgiserver
from jsonrpc import jsonrpc_handler_router as jrpc

# we are using a custom version of subprocess.Popen - PopenIO 
# with communicateIO() method that starts reading into mem
# and switches to hard-drive persistence after mem threshold is crossed.
if sys.platform == 'cli':
    import subprocessio.subprocessio_ironpython as subprocess
else:
    import subprocess
try:
    # will fail on cPython
    t = subprocess.PopenIO
except:
    import subprocessio.subprocessio as subprocess

def assemble_ges_app(path_prefix = '.', repo_uri_marker = '', performance_settings = {}):
    '''
    Assembles basic WSGI-compatible application providing functionality of git-http-backend.

    path_prefix (Defaults to '.' = "current" directory)
        The path to the folder that will be the root of served files. Accepts relative paths.

    repo_uri_marker (Defaults to '')
        Acts as a "virtual folder" separator between decorative URI portion and
        the actual (relative to path_prefix) path that will be appended to
        path_prefix and used for pulling an actual file.

        the URI does not have to start with contents of repo_uri_marker. It can
        be preceeded by any number of "virtual" folders. For --repo_uri_marker 'my'
        all of these will take you to the same repo:
            http://localhost/my/HEAD
            http://localhost/admysf/mylar/zxmy/my/HEAD
        This WSGI hanlder will cut and rebase the URI when it's time to read from file system.

        Default of '' means that no cutting marker is used, and whole URI after FQDN is
        used to find file relative to path_prefix.

    returns WSGI application instance.
    '''

    repo_uri_marker = repo_uri_marker.decode('utf8')
    path_prefix = path_prefix.decode('utf8')
    settings = {"path_prefix": path_prefix.decode('utf8')}
    settings.update(performance_settings)

    selector = git_http_backend.WSGIHandlerSelector()
    # generic_handler = git_http_backend.StaticWSGIServer(**settings)

    if repo_uri_marker:
        marker_regex = r'(?P<decorative_path>.*?)(?:/'+ repo_uri_marker + ')'
    else:
        marker_regex = ''

    selector.add(
        marker_regex + r'/showvars',
        ShowVarsWSGIApp()
        )
    static_server = git_http_backend.StaticWSGIServer(path_prefix = r'C:\Users\ddotsenko\Desktop\Work\Projects\git_http_backend\ges\src\sammymvc')
    selector.add(
        marker_regex + r'/static/(?P<working_path>.*)$',
        GET = static_server,
        HEAD = static_server)
    selector.add(
        marker_regex + r'(?P<working_path>.*)$',
        GET = TestingGitPython(),
        HEAD = TestingGitPython())
    return selector

import git.utils
class TestingGitPython(object):
    def __init__(self, *args, **kw):
        path = r'C:\tmp\repotest'
        dirs = []
        for name in os.listdir(path):
            if os.path.isdir(os.path.join(path, name)): # and not name.startswith('.'):
                dirs.append(name)
            self.l = dict( ( (dn, git.utils.is_git_dir(os.path.join(path,dn))) for dn in dirs ) )

    def __call__(self, environ, start_response):
        status = '200 OK'
        response_headers = [('Content-type','text/plain')]
        start_response(status, response_headers)
        yield "TESTING GIT-PYTHON\n\n"
#        for key in sorted(environ.keys()):
#            yield '%s = %s\n' % (key, unicode(environ[key]).encode('utf8'))
        for key, value in self.l.items():
            yield key + ' ' + str(value) + '\n'

class ShowVarsWSGIApp(object):
    def __init__(self, *args, **kw):
        pass
    def __call__(self, environ, start_response):
        status = '200 OK'
        response_headers = [('Content-type','text/plain')]
        start_response(status, response_headers)
        for key in sorted(environ.keys()):
            yield '%s = %s\n' % (key, unicode(environ[key]).encode('utf8'))

if __name__ == "__main__":
    _help = r'''
git_http_backend.py - Python-based server supporting regular and "Smart HTTP"
	
Note only the folder that contains folders and object that you normally see
in .git folder is considered a "repo folder." This means that either a
"bare" folder name or a working folder's ".git" folder will be a "repo" folder
discussed in the examples below.

When "repo-auto-create on Push" is used, the server automatically creates "bare"
repo folders.

Note, the folder does NOT have to have ".git" in the name to be a "repo" folder.
You can name bare repo folders whatever you like. If the signature (right files
and folders are found inside) matches a typical git repo, it's a "repo."

Options:
--path_prefix (Defaults to '.' - current directory)
	Serving contents of folder path passed in. Accepts relative paths,
	including things like "./../" and resolves them agains current path.

	If you set this to actual .git folder, you don't need to specify the
	folder's name on URI.

--repo_uri_marker (Defaults to '')
	Acts as a "virtual folder" - separator between decorative URI portion
	and the actual (relative to path_prefix) path that will be appended
	to path_prefix and used for pulling an actual file.

	the URI does not have to start with contents of repo_uri_marker. It can
	be preceeded by any number of "virtual" folders.
	For --repo_uri_marker 'my' all of these will take you to the same repo:
		http://localhost/my/HEAD
		http://localhost/admysf/mylar/zxmy/my/HEAD
	If you are using reverse proxy server, pick the virtual, decorative URI
	prefix / path of your choice. This hanlder will cut and rebase the URI.

	Default of '' means that no cutting marker is used, and whole URI after
	FQDN is used to find file relative to path_prefix.

--port (Defaults to 8080)

Examples:

cd c:\myproject_workingfolder\.git
c:\tools\git_http_backend\GitHttpBackend.py --port 80
	(Current path is used for serving.)
	This project's repo will be one and only served directly over
	 http://localhost/

cd c:\repos_folder
c:\tools\git_http_backend\GitHttpBackend.py 
	(note, no options are provided. Current path is used for serving.)
	If the c:\repos_folder contains repo1.git, repo2.git folders, they 
	become available as:
	 http://localhost:8080/repo1.git  and  http://localhost:8080/repo2.git

~/myscripts/GitHttpBackend.py --path_prefix "~/somepath/repofolder" --repo_uri_marker "myrepo"
	Will serve chosen repo folder as http://localhost/myrepo/ or
	http://localhost:8080/does/not/matter/what/you/type/here/myrepo/
	This "repo uri marker" is useful for making a repo server appear as a
	part of some REST web application or make it appear as a part of server
	while serving it from behind a reverse proxy.

./GitHttpBackend.py --path_prefix ".." --port 80
	Will serve the folder above the "git_http_backend" (in which 
	GitHttpBackend.py happened to be located.) A functional url could be
	 http://localhost/git_http_backend/GitHttpBackend.py
	Let's assume the parent folder of git_http_backend folder has a ".git"
	folder. Then the repo could be accessed as:
	 http://localhost/.git/
	This allows GitHttpBackend.py to be "self-serving" :)
'''
    import sys

    command_options = {
            'path_prefix' : '.',
            'repo_uri_marker' : '',
            'port' : '8888'
        }
    lastKey = None
    for item in sys.argv:
        if item.startswith('--'):
            command_options[item[2:]] = True
            lastKey = item[2:]
        elif lastKey:
            command_options[lastKey] = item.strip('"').strip("'")
            lastKey = None

    path_prefix = os.path.abspath( command_options['path_prefix'] )

    if 'help' in command_options:
        print _help
    else:
        app = assemble_ges_app(
            path_prefix = path_prefix,
            repo_uri_marker = command_options['repo_uri_marker']
        )
        
#        from cherrypy import wsgiserver
#        httpd = wsgiserver.CherryPyWSGIServer(('127.0.0.1',int(command_options['port'])),app)
        from wsgiref import simple_server
        httpd = simple_server.make_server('127.0.0.1',int(command_options['port']),app)

        if command_options['repo_uri_marker']:
            _s = '"/%s/".' % command_options['repo_uri_marker']
            example_URI = '''http://localhost:%s/whatever/you/want/here/%s/myrepo.git
    (Note: "whatever/you/want/here" cannot include the "/%s/" segment)''' % (
            command_options['port'],
            command_options['repo_uri_marker'],
            command_options['repo_uri_marker'])
        else:
            _s = 'not chosen.'
            example_URI = 'http://localhost:%s/myrepo.git' % (command_options['port'])
        print '''
===========================================================================
Run this command with "--help" option to see available command-line options

Starting git-http-backend server...
	Port: %s
	Chosen repo folders' base file system path: %s
	URI segment indicating start of git repo foler name is %s

Example repo url would be:
    %s

Use Keyboard Interrupt key combination (usually CTRL+C) to stop the server
===========================================================================
''' % (command_options['port'], path_prefix, _s, example_URI)

#        # running with CherryPy's WSGI Server
#        try:
#            httpd.start()
#        except KeyboardInterrupt:
#            pass
#        finally:
#            httpd.stop()
        # running with cPython's builtin WSGIREF
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
