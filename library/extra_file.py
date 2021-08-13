#!/usr/bin/python
# WANT JSON

from ansible.module_utils.basic import *
import json
import requests
from traceback import format_exc

class NotFoundError(Exception):
    pass

def get(username, password, name):
    response = requests.get(
        "http://localhost:9070/api/tm/6.0/config/active/extra_files/{}".format(name),
        auth=(username, password)
    )
    if response.status_code == 200:
        try:
            return response.json()
        except ValueError:
            return response.text
    elif response.status_code == 404:
        raise NotFoundError()
    else:
        response.raise_for_status()


def delete(username, password, name):
    response = requests.delete(
        "http://localhost:9070/api/tm/6.0/config/active/extra_files/{}".format(name),
        auth=(username, password)
    )
    if response.status_code != 204:
        response.raise_for_status


def put(username, password, name, data):
    response = requests.put(
        "http://localhost:9070/api/tm/6.0/config/active/extra_files/{}".format(name),
        auth=(username, password),
        headers={"Content-Type": "application/octet-stream"},
        data=data
    )
    if response.status_code not in [204]:
        response.raise_for_status()


def check_changes(module):
    try:
        # Get full object configuration from vTM
        data = get(module.params['username'], module.params['password'], module.params['name'])
        if module.params['state'] == "absent":
            return True
    except NotFoundError:
        # If the object doesn't exist, reconcile this with desired state
        if module.params['state'] == "absent":
            return False
        else:
            return True
    return data != module.params['content']


def execute(module):
    if module.params['state'] == "absent":
        delete(module.params['username'], module.params['password'], module.params['name'])
    else:
        data = module.params['content']
        put(module.params['username'], module.params['password'], module.params['name'], data)


def main():
    object_type = "extra_files"
    argument_spec = { 
        "name": {"required": True},
        "state": {"default": "present", "choices": ["present", "absent"]},
        "username": {"default": "admin"},
        "password": {},
        "content": {"type": "str"}
    }

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True
    )

    will_change = check_changes(module)

    if module.check_mode or will_change is False:
        module.exit_json(changed=will_change)

    try:
        execute(module)
        module.exit_json(changed=True)
    except requests.exceptions.HTTPError as e:
        module.fail_json(
            msg="An unexpected response was returned from the vTM => "
                "Status code {}, message '{}'".format(
                    e.response.status_code, e.response.text
                )
        )
    except Exception as e:
        module.fail_json(msg="An unexpected error occured: {}, {}".format(
            e, format_exc()
        ))


if __name__ == '__main__':
    main()
