import requests
import urllib
import base64
from flaskr.models import File
from flaskr.models import Directory
from flaskr.models import db
from flask import current_app

def apply_args_to_url(url, **kwargs):
    url = url.replace('{/', '/{')
    return url.format(**kwargs)


def get_commit_of_default_branch(repo):
    branch = repo['default_branch']
    branches_url = repo['branches_url']
    response = requests.get(apply_args_to_url(branches_url, branch=branch))
    return response.json()['commit']


def decode_content(content, encoding):
    decode_func = {
        'base64': base64.b64decode
    }

    return decode_func[encoding](content)
    

def traverse_tree(tree_url, project_id):
    response = requests.get(tree_url)
    body = response.json()

    root_dir = Directory(project_id=project_id,
            git_hash=body['sha'])

    _traverse(body['tree'], root_dir, project_id)


def _traverse(tree, parent_dir, project_id):
    for o in tree:
        if o['type'] == 'blob':
            f = File(file_name=o['path'],
                    parent_dir=parent_dir,
                    git_hash=o['sha'])
            db.session.add(f)
            db.session.commit()
        
        if o['type'] == 'tree':
            d = Directory(dir_name = o['path'],
                    project_id=project_id,
                    dir_parent=parent_dir,
                    git_hash=o['sha'])
            db.session.add(d)
            db.session.commit()

            response = requests.get(o['url'])
            body = response.json()
            _traverse(body['tree'], d, project_id)

