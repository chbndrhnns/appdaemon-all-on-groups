"""all-on-groups

@chbndrhnns / https://github.com/chbndrhnns/appdaemon-all-on-groups
"""

__version__ = "0.8.3"

from appdaemon.plugins.hass import hassapi as hass

ATTRIBUTE_NAME = "all_on"
ALL_ON_SENSOR_SUFFIX = f"_{ATTRIBUTE_NAME}"
APP_NAMESPACE = "default"
ADMIN_NAMESPACE = "admin"
CREATOR_KEY = "created_by"
ASSIGNED_ENTITIES_KEY = "entity_id"
CREATOR_VALUE = "AllOnGroups"
TARGET_ENTITY_TYPE = "binary_sensor"


class ADEvents:
    app_init = "app_initialized"
    app_terminated = "app_terminated"


def create_group_name(entity_id):
    """Returns the name of the virtual sensor that should be created"""
    name_with_out_type = "".join(entity_id.split(".")[1:])
    return f"{TARGET_ENTITY_TYPE}.{name_with_out_type}{ALL_ON_SENSOR_SUFFIX}"


class AllOnGroups(hass.Hass):

    def initialize(self):
        self.log("Initializing %s...", self.__class__.__name__)

        self._supported_entities = self.find_supported_entities()  # noqa
        self._registry = {}  # noqa
        self.cleanup()

        if self._supported_entities:
            self.log(f"Found supported devices: {self._supported_entities}")
            self.add_app_event_listeners()
            self.add_state_listeners()
        else:
            self.log(f"Found no supported devices")

    def cleanup(self):
        """Remove all existing virtual sensors"""
        self.log("Cleaning up existing virtual sensors...")
        for group in self.find_existing_groups():
            self.delete_group(group)

    def get_all_on_attribute(self, entity_id):
        """Return the `all_on` attribute for an entity"""
        return self.get_state(entity_id, attribute=ATTRIBUTE_NAME, default=None)

    def set_group_state(self, entity_id, group_name, val):
        """Update a group's state. Group is created if it does not exist"""
        if val not in {True, False}:
            self.log(f"Got invalid value for {group_name}: {val}")
        self.log("%s: setting to %s", group_name, val)
        self.set_state(
            group_name,
            state=val,
            attributes={
                "created_by": CREATOR_VALUE,
                "name": f"All lights are on for {entity_id}",
                "entity_id": self.get_state(entity_id, attribute=ASSIGNED_ENTITIES_KEY, default="")
            }
        )

    def is_created_by_appdaemon(self, entity_id):
        """Returns True if an entity was created by AppDaemon"""
        return self.get_state(entity_id, attribute=CREATOR_KEY, default=None) == CREATOR_VALUE

    def find_existing_groups(self):
        """Returns a set of the entities that have already been created"""
        return {s for s in self.get_state() if self.is_created_by_appdaemon(s)}

    def add_state_listeners(self):
        """Register state listeners"""
        for sensor in self._supported_entities:
            self.listen_state(self._sensor_state_changed_callback, sensor, attribute=ATTRIBUTE_NAME)

    def add_app_event_listeners(self):
        """Register events for app init and shutdown"""
        self.set_namespace(ADMIN_NAMESPACE)
        self.listen_event(self.create_groups, event=ADEvents.app_init)
        self.listen_event(self.delete_groups, event=ADEvents.app_terminated)
        self.set_namespace(APP_NAMESPACE)

    def find_supported_entities(self):
        """Returns all found sensors"""
        return {
            s for s in self.get_state() if self.get_all_on_attribute(s) is not None
        }

    def create_groups(self, event_name, data, kwargs):
        """Create a group for the actual entity"""
        # for sensor in ['light.lights_kitchen2']:
        for sensor in self._supported_entities:
            self.create_group(sensor)

    def create_group(self, entity_id):
        """Create a group for an entity"""
        group_name = create_group_name(entity_id)
        current_state = self.get_all_on_attribute(entity_id)
        self.set_group_state(entity_id, group_name, current_state)
        self._registry.update({entity_id: group_name})

    def delete_group(self, entity_id):
        """Remove a virtual sensor that was created by the app"""
        self.log("Removing %s...", entity_id)

        self.remove_entity(entity_id)
        try:
            del self._registry[entity_id]
        except KeyError:
            pass

    def delete_groups(self, event_name, data, kwargs):
        """Delete all created virtual entities"""
        # for sensor in ['light.lights_kitchen2']:
        for sensor in self._registry.values():
            self.delete_group(sensor)

    def _sensor_state_changed_callback(self, entity_id, attribute, old, new, kwargs):
        self.log("%s: '%s' changed from %s to %s", entity_id, attribute, old, new)

        if virtual_sensor := self._registry.get(entity_id):
            new_attribute = self.get_all_on_attribute(entity_id)

            if new_attribute != self.get_all_on_attribute(virtual_sensor):
                self.set_group_state(entity_id, virtual_sensor, new_attribute)
