# pulse-vtm-ansible
Ansible module for configuring Pulse Secure Virtual Traffic Manager (UNOFFICIAL) 

_**This module is not provided by, nor supported by, Pulse Secure.**_

Please use the tagged release that corresponds to the relevant REST API version for the Pulse vTM version you are running.

## Content 

"library" folder - this contains the resources that represent Pulse vTM configuration objects.

"examples" folder - this contains an example *hosts* file and some example playbooks.  The examples assume that one of the "library" folders is present in the same directory.

## Usage:

Pulse vTM supports two distinct object types: JSON-based objects (eg. virtual servers, pools, etc.) and text-based objects (eg. rules and server certificates).  These objects are represented in Ansible as objects with the singular form of the names used by the vTM REST API.

### JSON-based objects:

These support four parameters:
- name: (str) the name of the resource to create.
- state: (str) "present" or "absent" (default: "present").
- password: (str) the admin password of the vTM on which to create the resource.  NB. for security/flexibility, it is recommended to use a variable for this.
- properties: (dict) the properties the configurtaion object should possess in the case that "state" is "present".  The properties field is not validated within the Ansible module, but MUST be structured as described in the Pulse vTM REST API manual for the object type concerned.  For example:

```yaml
virtual_server:
    name: test_vs
    password: "{{ admin_password }}"
    properties:
        basic:
            enabled: True
            port: 1234
            pool: test_pool
        web_cache:
            enabled: True
            control_out: "no-cache"
```

### Text-based objects:

These support four parameters:
- name: (str) the name of the resource to create.
- state: (str) "present" or "absent" (default: "present").
- password: (str) the admin password of the vTM on which to create the resource.  NB. for security/flexibility, it is recommended to use a variable for this.
- content: (str) the text to store in the configuration object.

```yaml
rule:
    name: test_rule
    password: "{{ admin_password }}"
    content: |
        $rabbitTracks = http.getHeader("X-Rabbit-Tracks");

        if($rabbitTracks == "fresh")
        {
            http.sendResponse("200 OK", "text/plain", "Kill the rabbit!", "");
        }
```

## Examples:

To run the examples:

- you should have a layout such as the following:

```bash
$ ls -R examples
configure_vtm.yaml   hosts                library              reconfigure_vtm.yaml unconfigure_vtm.yaml

examples/library:
action.py                client_key.py            global_settings.py       monitor.py               profile.py               security.py              user_authenticator.py
action_program.py        cloud_api_credential.py  keytab.py                monitor_script.py        protection.py            server_key.py            user_group.py
application_firewall.py  custom.py                krb5conf.py              nat.py                   rate.py                  service_level_monitor.py virtual_server.py
bandwidth.py             event_type.py            license_key.py           persistence.py           rule.py                  ticket_key.py            zone.py
bgpneighbor.py           extra_file.py            location.py              pool.py                  rule_authenticator.py    traffic_ip_group.py      zone_file.py
ca.py                    glb_service.py           log_export.py            principal.py             scope.py                 traffic_manager.py
```

- Passwordless SSH should be configured on the vTM instance(s) you wish to configure.
- The *hosts* file should be set with the vTM list and credentials to use.
- Run the command:
```bash
$ ansible-playbook -i hosts (|re|un)configure_vtm.yaml
```
- Observe the new configuration in the vTM UI.
