#!/usr/bin/python
# WANT JSON

from ansible.module_utils.basic import *
import json
import requests
from traceback import format_exc

class NotFoundError(Exception):
    pass

def get(password, name):
    response = requests.get(
        "http://localhost:9070/api/tm/3.8/config/active/principals/{}".format(name),
        auth=("admin", password)
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


def delete(password, name):
    response = requests.delete(
        "http://localhost:9070/api/tm/3.8/config/active/principals/{}".format(name),
        auth=("admin", password)
    )
    if response.status_code != 204:
        response.raise_for_status


def put(password, name, data):
    response = requests.put(
        "http://localhost:9070/api/tm/3.8/config/active/principals/{}".format(name),
        auth=("admin", password),
        headers={"Content-Type": "application/json"},
        data=data
    )
    if response.status_code not in [200, 201]:
        response.raise_for_status()


def sort_table(section, field, table):
    table_keys = {}
    sort_by = table_keys[section][field]
    sort_tuple = ", ".join("x['{}']".format(field) for field in sort_by)
    return sorted(table, key=lambda x: (eval(sort_tuple)))


def check_changes(module):
    try:
        # Get full object configuration from vTM
        data = get(module.params['password'], module.params['name'])
        if module.params['state'] == "absent":
            return True
    except NotFoundError:
        # If the object doesn't exist, reconcile this with desired state
        if module.params['state'] == "absent":
            return False
        else:
            return True
    # Check individual config key settings
    for section, fields in module.params['properties'].items():
        for key, value in fields.items():
            if isinstance(value, list) and isinstance(value[0], dict):
            # Field is a table so we have to sort it and intersect fields
                specified_table = sort_table(section, key, value)
                vtm_table = sort_table(
                    section, key, data['properties'][section][key]
                )
                if len(vtm_table) != len(specified_table):
                    return True
                for index, row in enumerate(specified_table):
                    for field_name, field_value in row.items():
                        if vtm_table[index][field_name] != field_value:
                            return True
            elif data['properties'][section][key] != value:
            # Field is not a table so a straight value comparison works
                return True
    return False



def execute(module):
    if module.params['state'] == "absent":
        delete(module.params['password'], module.params['name'])
    else:
        data = json.dumps({'properties': module.params['properties']})
        put(module.params['password'], module.params['name'], data)


def main():
    object_type = "principals"
    argument_spec = { 
        "name": {"required": True},
        "state": {"default": "present", "choices": ["present", "absent"]},
        "password": {},
        "properties": {"type": "dict"}
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
