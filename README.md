# appdaemon-all-on-groups

[Deconz] groups are exposed to Home Assistant with an 
`all_on` attribute which indicates if all lights in a group
are currently switched on.

This app exposes this attribute as an additional group. For this
purpose, 
- it looks for all light entities that have an `all_on` 
attribute,
- it creates a group with an `_all_on` suffix,
- it adds a listener to update the state of the groups.


