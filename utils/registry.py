# utils/base_model.py
from typing import TypeVar
from pydantic import BaseModel
import uuid
from weakref import WeakKeyDictionary, WeakValueDictionary
from copy import deepcopy


T = TypeVar('T', bound=BaseModel)


class ChangeCommand:
    """Represents a change to an object that can be undone/redone"""

    def __init__(self, obj_id, field_name, old_value, new_value):
        self.obj_id = obj_id
        self.field_name = field_name
        self.old_value = deepcopy(old_value)
        self.new_value = deepcopy(new_value)

    def undo(self, registry):
        """Revert the change"""
        obj = registry.get_object(self.obj_id)
        if obj:
            setattr(obj, self.field_name, self.old_value)

    def redo(self, registry):
        """Reapply the change"""
        obj = registry.get_object(self.obj_id)
        if obj:
            setattr(obj, self.field_name, self.new_value)


class Registry:
    def __init__(self):
        self.object_ids = WeakKeyDictionary()  # object -> id
        self.id_objects = WeakValueDictionary()  # id -> object

        # Command history for undo/redo
        self.commands = []
        self.command_position = -1

        # Flag to disable command recording during undo/redo
        self.recording_enabled = True

    def register(self, obj):
        """Register an object with the registry"""
        if not isinstance(obj, RegisteredModel):
            return None

        if obj in self.object_ids:
            return self.object_ids[obj]

        obj_id = str(uuid.uuid4())
        self.object_ids[obj] = obj_id
        self.id_objects[obj_id] = obj

        return obj_id

    def record_change(self, obj, field_name, old_value, new_value):
        """Record a change for undo/redo"""
        if not self.recording_enabled:
            return

        obj_id = self.get_id(obj)
        if not obj_id:
            return

        # Create a command for this change
        command = ChangeCommand(obj_id, field_name, old_value, new_value)

        # If we're in the middle of the command history, truncate
        if self.command_position < len(self.commands) - 1:
            self.commands = self.commands[:self.command_position + 1]

        # Add the new command
        self.commands.append(command)
        self.command_position = len(self.commands) - 1

    def undo(self):
        """Undo the last change"""
        if self.command_position >= 0:
            # Disable recording to prevent recording the undo itself
            self.recording_enabled = False

            # Undo the command
            self.commands[self.command_position].undo(self)
            self.command_position -= 1

            # Re-enable recording
            self.recording_enabled = True
            return True
        return False

    def redo(self):
        """Redo the previously undone change"""
        if self.command_position < len(self.commands) - 1:
            # Disable recording
            self.recording_enabled = False

            # Move to next command and redo it
            self.command_position += 1
            self.commands[self.command_position].redo(self)

            # Re-enable recording
            self.recording_enabled = True
            return True
        return False

    def get_id(self, obj):
        """Get ID for an object"""
        return self.object_ids.get(obj)

    def get_object(self, obj_id):
        """Get object by ID"""
        return self.id_objects.get(obj_id)


# Global registry
REGISTRY = Registry()


class RegisteredModel(BaseModel):
    """Base class for models with undo/redo support"""

    def __hash__(self):
        # Use Python's built-in object identity
        return id(self)

    def __eq__(self, other):
        # For mutable objects, equality should check identity
        # not content equality (which is Pydantic's default)
        return self is other

    def model_post_init(self, __context) -> None:
        super().model_post_init(__context)
        # Register with registry
        REGISTRY.register(self)

    def __setattr__(self, name, value):
        """Override attribute setting to record changes"""
        if hasattr(self, name):
            # Record the change before it happens
            old_value = getattr(self, name)
            REGISTRY.record_change(self, name, old_value, value)

        # Perform the actual change
        super().__setattr__(name, value)
