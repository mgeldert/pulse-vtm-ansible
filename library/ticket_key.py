#!/usr/bin/python
# WANT JSON

from ansible.module_utils.basic import *
import json
import requests
from traceback import format_exc


class NotFoundError(Exception):
    pass


class InvalidFieldTypeError(Exception):
    pass


def get(password, name):
    """
    Perform an HTTP GET request to the vTM REST API.
    """
    response = requests.get(
        "http://localhost:9070/api/tm/5.1/config/active/ticket_keys/{}".format(name),
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
    """
    Perform an HTTP DELETE request to the vTM REST API.
    """
    response = requests.delete(
        "http://localhost:9070/api/tm/5.1/config/active/ticket_keys/{}".format(name),
        auth=("admin", password)
    )
    if response.status_code != 204:
        response.raise_for_status


def put(password, name, data):
    """
    Perform an HTTP PUT request to the vTM REST API.
    """
    response = requests.put(
        "http://localhost:9070/api/tm/5.1/config/active/ticket_keys/{}".format(name),
        auth=("admin", password),
        headers={"Content-Type": "application/json"},
        data=data
    )
    if response.status_code not in [200, 201]:
        response.raise_for_status()


def sort_table(section, field, table):
    """
    Sort a vTM table field by 'key' field(s).

    Params:
        section     (string) Section of the vTM object configuration.
        field       (string) Name of the vTM table field.
        table       (list)   Table data to sort.

    Returns:
        list        Table data sorted by 'key' fields, as defined by the
                    vTM REST schema.
    """
    table_keys = {}
    sort_by = table_keys[section][field]
    sort_tuple = ", ".join("x['{}']".format(field) for field in sort_by)
    return sorted(table, key=lambda x: (eval(sort_tuple)))


def key_in_table(section, field, row, table):
    """
    Test for presence of row key field values in a data table.

    Params:
        section     (string) Section of the vTM object configuration.
        field       (string) Name of the vTM table field.
        row         (dict)   A row of data from an existing vTM configuration.
        table       (list)   The table of data to be appended to the existing
                             table data.

    Returns:
        bool        True if the key field(s) of the existing data row match a
                    row from the newly-specified table data, else False.
    """
    table_keys = {}
    try:
        key_fields = table_keys[section][field]
    except KeyError:
        raise InvalidFieldTypeError(
            "{} -> {}".format(section, field)
        )
    for table_row in table[section][field]:
        key_matched = True
        for key in key_fields:
            if table_row[key] != row[key]:
                key_matched = False
        if key_matched is True:
            return True
    return False


def process_table_appends(current_props, new_props, tables_to_append):
    """
    Append rows to the designated existing table fields.

    Params:
        current_props     (dict) The current configuration of the vTM resource.
        new_props         (dict) The new configuration specified to Ansible.
        tables_to_append  (dict) Map of table fields that should have the new

    Returns:
        dict              new_props with existing data in designated table
                          fields appended to the new row values (new values
                          take precedence where there is a key field(s)
                          collision.
    """
    table_keys = {}
    for section, fields in tables_to_append.items():
        for field in fields:
            # Check that the specified field is a table field
            if(section not in table_keys
            or field not in table_keys[section]):
                raise InvalidFieldTypeError(
                    "{} -> {}".format(section, field)
                )
            # Get the current value of the table field
            try:
                table_field = current_props['properties'][section][field]
            except KeyError:
                raise NotFoundError("{} -> {}".format(section, field))
            # Check each row in the existing table for a key matching the
            #  new data
            for row in table_field:
                if key_in_table(section, field, row, new_props) is False:
                    # If the key field(s) don't match any of the new entries,
                    #  append the existing row to the new table data
                    new_props[section][field].append(row)
    return new_props


def check_changes(module):
    """
    Check if applying new config will change existing config.

    Returns:
        bool    True if a change is required, else False.
    """
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
    if module.params['append_to_tables'] is None:
        properties = module.params['properties']
    else:
        try:
            properties = process_table_appends(
                data,
                module.params['properties'],
                module.params['append_to_tables']
            )
        except (NotFoundError, InvalidFieldTypeError) as e:
            module.fail_json(
                msg="Unable to check table {}".format(e)
            )

    for section, fields in properties.items():
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
        
        if module.params['append_to_tables'] is None:
            data = json.dumps({'properties': module.params['properties']})
        else:
            current_properties = get(
                module.params['password'], module.params['name']
            )
            try:
                data = process_table_appends(
                    current_properties,
                    module.params['properties'],
                    module.params['append_to_tables']
                )
                data = json.dumps({'properties': data})
            except NotFoundError as e:
                module.fail_json(
                    msg="Unable to append to table: {} not found".format(e)
                )
            except InvalidFieldTypeError as e:
                module.fail_json(
                    msg="Unable to append to table: {} not a table".format(e)
                )
    
        put(module.params['password'], module.params['name'], data)


def main():
    object_type = "ticket_keys"
    argument_spec = { 
        "name": {"required": True},
        "state": {"default": "present", "choices": ["present", "absent"]},
        "password": {},
        "properties": {"type": "dict"},
        "append_to_tables": {"type": "dict"}
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
