'''
Considerations for implementation of EntityReferenceContainer
If you decide to go with the EntityReferenceContainer approach, here are some considerations:

Type checking: The current implementation might struggle with more complex type hints (like Optional[StructuralMaterial]). You may need more sophisticated type analysis.
Generics support: If you use generic types with Identifiable objects, additional logic might be needed.
Circular references: Be careful with circular references between objects, which could cause issues during serialization/deserialization.
Memory usage: Storing both objects and IDs uses slightly more memory, but the tradeoff is worthwhile for clarity and functionality.

Overall, I think your EntityReferenceContainer approach is the most elegant solution to the problem, and it's worth implementing despite these considerations. It's a good example of the DRY principle (Don't Repeat Yourself) applied effectively.

BASIC EXAMPLE CODE:

from typing import Dict, Any, Type, ClassVar, Set, Optional, get_type_hints, List, cast
from pydantic import BaseModel, Field, model_validator, ConfigDict
from utils.base_model import ImmutableModel
from utils.identifiable import Identifiable

class EntityReferenceContainer(ImmutableModel):
    """
    Base class for models that contain references to identifiable entities.
    Automatically tracks references to identifiable objects and their IDs.
    """
    # Store entity IDs in a dictionary: field_name -> entity_id
    entity_ids: Dict[str, str] = Field(default_factory=dict)

    # Keep track of which fields are identifiable references (defined in subclasses)
    _identifiable_fields: ClassVar[Set[str]] = set()

    def __init_subclass__(cls, **kwargs):
        """Initialize subclass with tracking of Identifiable field references."""
        super().__init_subclass__(**kwargs)

        # Analyze class annotations to find Identifiable fields
        hints = get_type_hints(cls)
        identifiable_fields = set()

        for field_name, field_type in hints.items():
            # Skip special fields and the entity_ids field itself
            if field_name.startswith('_') or field_name == 'entity_ids':
                continue

            # Check if this field type is a subclass of Identifiable
            try:
                if isinstance(field_type, type) and issubclass(field_type, Identifiable):
                    identifiable_fields.add(field_name)
            except TypeError:
                # Handle generic types, Optional, etc.
                pass

        # Store the identified fields in the class
        cls._identifiable_fields = identifiable_fields

    @model_validator(mode='after')
    def extract_entity_ids(self) -> 'EntityReferenceContainer':
        """Extract IDs from all identifiable entity references."""
        entity_ids = dict(self.entity_ids) if self.entity_ids else {}

        # Check all potential identifiable fields
        for field_name in self._identifiable_fields:
            entity = getattr(self, field_name, None)

            # Skip None values
            if entity is None:
                continue

            # Extract ID if this is an Identifiable
            if isinstance(entity, Identifiable) and hasattr(entity, 'id'):
                entity_ids[field_name] = entity.id

        # Also look for {field_name}_id fields from deserialized data
        for field_name in self._identifiable_fields:
            id_field_name = f"{field_name}_id"
            if hasattr(self, id_field_name):
                entity_id = getattr(self, id_field_name)
                if entity_id is not None:
                    entity_ids[field_name] = entity_id

        # Only update if there are changes
        if entity_ids != self.entity_ids:
            object.__setattr__(self, 'entity_ids', entity_ids)

        return self

    def get_entity_id(self, field_name: str) -> Optional[str]:
        """Get the ID for a specific entity field."""
        return self.entity_ids.get(field_name)

    def model_dump(
        self,
        *,
        mode: str = "python",
        include: Optional[Set[str]] = None,
        exclude: Optional[Set[str]] = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: bool = True,
    ) -> Dict[str, Any]:
        """
        Override the model_dump method to ensure that entity IDs are
        included in the serialized output.
        """
        # Call the parent method to get the base dictionary
        result = super().model_dump(
            mode=mode,
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings,
        )

        # Add entity IDs as explicit fields
        for field_name, entity_id in self.entity_ids.items():
            id_field_name = f"{field_name}_id"
            result[id_field_name] = entity_id

        return result

    @classmethod
    def model_validate(cls, obj: Any, **kwargs):
        """
        Override the model_validate method to handle deserialization from
        data that may include entity IDs but not the actual entity objects.
        """
        # If we have _id fields but not the entity fields, create placeholder attributes
        if isinstance(obj, dict):
            # Note existing entity fields and their corresponding ID fields
            entity_fields = set()
            id_fields = {}

            for field_name in cls._identifiable_fields:
                id_field_name = f"{field_name}_id"

                # Check if we have an ID field but not the entity
                if id_field_name in obj and field_name not in obj:
                    id_fields[field_name] = obj[id_field_name]

                # Track existing entity fields
                if field_name in obj:
                    entity_fields.add(field_name)

            # Ensure entity_ids is in the data
            if 'entity_ids' not in obj:
                obj['entity_ids'] = {}

            # Add any ID fields to entity_ids
            for field_name, entity_id in id_fields.items():
                obj['entity_ids'][field_name] = entity_id

        # Proceed with normal validation
        return super().model_validate(obj, **kwargs)

    def resolve_references(self, entity_registry: Dict[str, Dict[str, Identifiable]]) -> 'EntityReferenceContainer':
        """
        Resolve entity references from their IDs.

        Args:
            entity_registry: A dictionary mapping entity types to a dictionary of ID -> entity

        Returns:
            A new instance with resolved entity references
        """
        # Get the current data for creating a new instance
        data = self.model_dump()

        # Remove the generated ID fields
        for field_name in self._identifiable_fields:
            id_field_name = f"{field_name}_id"
            if id_field_name in data:
                del data[id_field_name]

        # Get the entity type hints
        hints = get_type_hints(self.__class__)

        # Resolve each reference field
        for field_name in self._identifiable_fields:
            entity_id = self.get_entity_id(field_name)
            if entity_id is not None:
                # Determine the entity type
                entity_type = hints.get(field_name)

                if entity_type and isinstance(entity_type, type):
                    entity_type_name = entity_type.__name__

                    # Look up the entity in the registry
                    if entity_type_name in entity_registry:
                        type_registry = entity_registry[entity_type_name]
                        if entity_id in type_registry:
                            # Found it - add to the data
                            data[field_name] = type_registry[entity_id]

        # Create a new instance with the resolved references
        return self.__class__.model_validate(data)





Here's how we could extend the EntityReferenceContainer to support deserialization:






from typing import Dict, Any, Type, ClassVar, Set, Optional, get_type_hints, List, cast
from pydantic import BaseModel, Field, model_validator, ConfigDict
from utils.base_model import ImmutableModel
from utils.identifiable import Identifiable

class EntityReferenceContainer(ImmutableModel):
    """
    Base class for models that contain references to identifiable entities.
    Automatically tracks references to identifiable objects and their IDs.
    """
    # Store entity IDs in a dictionary: field_name -> entity_id
    entity_ids: Dict[str, str] = Field(default_factory=dict)

    # Keep track of which fields are identifiable references (defined in subclasses)
    _identifiable_fields: ClassVar[Set[str]] = set()

    def __init_subclass__(cls, **kwargs):
        """Initialize subclass with tracking of Identifiable field references."""
        super().__init_subclass__(**kwargs)

        # Analyze class annotations to find Identifiable fields
        hints = get_type_hints(cls)
        identifiable_fields = set()

        for field_name, field_type in hints.items():
            # Skip special fields and the entity_ids field itself
            if field_name.startswith('_') or field_name == 'entity_ids':
                continue

            # Check if this field type is a subclass of Identifiable
            try:
                if isinstance(field_type, type) and issubclass(field_type, Identifiable):
                    identifiable_fields.add(field_name)
            except TypeError:
                # Handle generic types, Optional, etc.
                pass

        # Store the identified fields in the class
        cls._identifiable_fields = identifiable_fields

    @model_validator(mode='after')
    def extract_entity_ids(self) -> 'EntityReferenceContainer':
        """Extract IDs from all identifiable entity references."""
        entity_ids = dict(self.entity_ids) if self.entity_ids else {}

        # Check all potential identifiable fields
        for field_name in self._identifiable_fields:
            entity = getattr(self, field_name, None)

            # Skip None values
            if entity is None:
                continue

            # Extract ID if this is an Identifiable
            if isinstance(entity, Identifiable) and hasattr(entity, 'id'):
                entity_ids[field_name] = entity.id

        # Also look for {field_name}_id fields from deserialized data
        for field_name in self._identifiable_fields:
            id_field_name = f"{field_name}_id"
            if hasattr(self, id_field_name):
                entity_id = getattr(self, id_field_name)
                if entity_id is not None:
                    entity_ids[field_name] = entity_id

        # Only update if there are changes
        if entity_ids != self.entity_ids:
            object.__setattr__(self, 'entity_ids', entity_ids)

        return self

    def get_entity_id(self, field_name: str) -> Optional[str]:
        """Get the ID for a specific entity field."""
        return self.entity_ids.get(field_name)

    def model_dump(
        self,
        *,
        mode: str = "python",
        include: Optional[Set[str]] = None,
        exclude: Optional[Set[str]] = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: bool = True,
    ) -> Dict[str, Any]:
        """
        Override the model_dump method to ensure that entity IDs are
        included in the serialized output.
        """
        # Call the parent method to get the base dictionary
        result = super().model_dump(
            mode=mode,
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings,
        )

        # Add entity IDs as explicit fields
        for field_name, entity_id in self.entity_ids.items():
            id_field_name = f"{field_name}_id"
            result[id_field_name] = entity_id

        return result

    @classmethod
    def model_validate(cls, obj: Any, **kwargs):
        """
        Override the model_validate method to handle deserialization from
        data that may include entity IDs but not the actual entity objects.
        """
        # If we have _id fields but not the entity fields, create placeholder attributes
        if isinstance(obj, dict):
            # Note existing entity fields and their corresponding ID fields
            entity_fields = set()
            id_fields = {}

            for field_name in cls._identifiable_fields:
                id_field_name = f"{field_name}_id"

                # Check if we have an ID field but not the entity
                if id_field_name in obj and field_name not in obj:
                    id_fields[field_name] = obj[id_field_name]

                # Track existing entity fields
                if field_name in obj:
                    entity_fields.add(field_name)

            # Ensure entity_ids is in the data
            if 'entity_ids' not in obj:
                obj['entity_ids'] = {}

            # Add any ID fields to entity_ids
            for field_name, entity_id in id_fields.items():
                obj['entity_ids'][field_name] = entity_id

        # Proceed with normal validation
        return super().model_validate(obj, **kwargs)

    def resolve_references(self, entity_registry: Dict[str, Dict[str, Identifiable]]) -> 'EntityReferenceContainer':
        """
        Resolve entity references from their IDs.

        Args:
            entity_registry: A dictionary mapping entity types to a dictionary of ID -> entity

        Returns:
            A new instance with resolved entity references
        """
        # Get the current data for creating a new instance
        data = self.model_dump()

        # Remove the generated ID fields
        for field_name in self._identifiable_fields:
            id_field_name = f"{field_name}_id"
            if id_field_name in data:
                del data[id_field_name]

        # Get the entity type hints
        hints = get_type_hints(self.__class__)

        # Resolve each reference field
        for field_name in self._identifiable_fields:
            entity_id = self.get_entity_id(field_name)
            if entity_id is not None:
                # Determine the entity type
                entity_type = hints.get(field_name)

                if entity_type and isinstance(entity_type, type):
                    entity_type_name = entity_type.__name__

                    # Look up the entity in the registry
                    if entity_type_name in entity_registry:
                        type_registry = entity_registry[entity_type_name]
                        if entity_id in type_registry:
                            # Found it - add to the data
                            data[field_name] = type_registry[entity_id]

        # Create a new instance with the resolved references
        return self.__class__.model_validate(data)
'''

import pytest
from typing import Dict, List, Optional, Set, Union, get_type_hints
from pydantic import BaseModel, Field, model_validator

from utils.base_model import ImmutableModel
from utils.identifiable import Identifiable
from utils.entity_reference_container import EntityReferenceContainer


# Fixture Models
class SimpleMaterial(ImmutableModel, Identifiable):
    """A simple material model for testing."""
    name: str = Field(description="Material name")
    density: float = Field(description="Material density")


class SimpleModel(ImmutableModel, Identifiable):
    """A simple behavioral model for testing."""
    name: str = Field(description="Model name")
    parameter: float = Field(description="Model parameter")


class BasicReferenceContainer(EntityReferenceContainer, Identifiable):
    """Basic container with single references."""
    name: str = Field(description="Container name")
    material: SimpleMaterial = Field(description="Reference to material")
    model: SimpleModel = Field(description="Reference to model")


class OptionalReferenceContainer(EntityReferenceContainer, Identifiable):
    """Container with optional references."""
    name: str = Field(description="Container name")
    material: Optional[SimpleMaterial] = Field(default=None, description="Optional material reference")
    model: Optional[SimpleModel] = Field(default=None, description="Optional model reference")


class ListReferenceContainer(EntityReferenceContainer, Identifiable):
    """Container with list references."""
    name: str = Field(description="Container name")
    materials: List[SimpleMaterial] = Field(default_factory=list, description="List of materials")


class NestedReferenceContainer(EntityReferenceContainer, Identifiable):
    """Container with nested references."""
    name: str = Field(description="Container name")
    basic_container: BasicReferenceContainer = Field(description="Nested reference container")


class UnionReferenceContainer(EntityReferenceContainer, Identifiable):
    """Container with union references."""
    name: str = Field(description="Container name")
    resource: Union[SimpleMaterial, SimpleModel] = Field(description="Union reference")


class SelfReferenceContainer(EntityReferenceContainer, Identifiable):
    """Container with self-references."""
    name: str = Field(description="Container name")
    parent: Optional["SelfReferenceContainer"] = Field(default=None, description="Parent reference")
    children: List["SelfReferenceContainer"] = Field(default_factory=list, description="Child references")


# Now rebuild for the forward references
SelfReferenceContainer.model_rebuild()


@pytest.fixture
def material():
    """Fixture for a simple material."""
    return SimpleMaterial.create(
        id="material_1",
        name="Steel",
        density=7850.0
    )


@pytest.fixture
def model():
    """Fixture for a simple model."""
    return SimpleModel.create(
        id="model_1",
        name="Linear Elastic",
        parameter=210000.0
    )


@pytest.fixture
def basic_container(material, model):
    """Fixture for a basic reference container."""
    return BasicReferenceContainer.create(
        id="container_1",
        name="Basic Container",
        material=material,
        model=model
    )


class TestEntityReferenceContainer:
    """Test suite for EntityReferenceContainer."""

    def test_basic_container_creation(self, material, model):
        """Test creating a basic container with references."""
        container = BasicReferenceContainer.create(
            id="container_1",
            name="Basic Container",
            material=material,
            model=model
        )

        # Test references are stored correctly
        assert container.material is material
        assert container.model is model

        # Test IDs are extracted correctly
        assert container.entity_ids["material"] == "material_1"
        assert container.entity_ids["model"] == "model_1"

        # Test ID accessor method
        assert container.get_entity_id("material") == "material_1"
        assert container.get_entity_id("model") == "model_1"

    def test_serialization(self, basic_container):
        """Test serialization includes entity IDs."""
        serialized = basic_container.model_dump()

        # Check basic properties
        assert serialized["id"] == "container_1"
        assert serialized["name"] == "Basic Container"

        # Check entity_ids dictionary is included
        assert "entity_ids" in serialized
        assert serialized["entity_ids"]["material"] == "material_1"
        assert serialized["entity_ids"]["model"] == "model_1"

        # Check individual ID fields are added
        assert "material_id" in serialized
        assert "model_id" in serialized
        assert serialized["material_id"] == "material_1"
        assert serialized["model_id"] == "model_1"

    def test_deserialization_with_ids_only(self, material, model):
        """Test deserializing from data with only IDs."""
        data = {
            "id": "container_1",
            "name": "Basic Container",
            "material_id": "material_1",
            "model_id": "model_1"
        }

        # Deserialize
        container = BasicReferenceContainer.model_validate(data)

        # Check basic properties
        assert container.id == "container_1"
        assert container.name == "Basic Container"

        # Check entity references are None (not resolved yet)
        assert container.material is None
        assert container.model is None

        # Check entity_ids are populated
        assert container.entity_ids["material"] == "material_1"
        assert container.entity_ids["model"] == "model_1"

    def test_reference_resolution(self, material, model):
        """Test resolving references from IDs."""
        # Create container with only IDs
        data = {
            "id": "container_1",
            "name": "Basic Container",
            "material_id": "material_1",
            "model_id": "model_1"
        }

        container = BasicReferenceContainer.model_validate(data)

        # Create entity registry
        registry = {
            "SimpleMaterial": {"material_1": material},
            "SimpleModel": {"model_1": model}
        }

        # Resolve references
        resolved = container.resolve_references(registry)

        # Check references are resolved
        assert resolved.material is material
        assert resolved.model is model

        # Check entity_ids are preserved
        assert resolved.entity_ids["material"] == "material_1"
        assert resolved.entity_ids["model"] == "model_1"

    def test_optional_references(self, material):
        """Test container with optional references."""
        # Create with only one reference
        container = OptionalReferenceContainer.create(
            id="container_1",
            name="Optional Container",
            material=material,
            model=None
        )

        # Check reference
        assert container.material is material
        assert container.model is None

        # Check entity_ids
        assert container.entity_ids["material"] == "material_1"
        assert "model" not in container.entity_ids

        # Test serialization
        serialized = container.model_dump()
        assert serialized["material_id"] == "material_1"
        assert "model_id" not in serialized  # Should not include None references

    def test_list_references(self, material):
        """Test container with list references."""
        # Create two materials
        material2 = SimpleMaterial.create(
            id="material_2",
            name="Aluminum",
            density=2700.0
        )

        # Create container with list reference
        container = ListReferenceContainer.create(
            id="container_1",
            name="List Container",
            materials=[material, material2]
        )

        # Test the references
        assert len(container.materials) == 2
        assert container.materials[0] is material
        assert container.materials[1] is material2

        # This is a more complex case - for now, just check
        # that entity_ids is empty since lists aren't handled yet
        assert "materials" not in container.entity_ids

    def test_nested_references(self, basic_container):
        """Test container with nested reference containers."""
        container = NestedReferenceContainer.create(
            id="nested_1",
            name="Nested Container",
            basic_container=basic_container
        )

        # Test the reference
        assert container.basic_container is basic_container

        # Test entity_ids
        assert container.entity_ids["basic_container"] == "container_1"

        # Test serialization
        serialized = container.model_dump()
        assert serialized["basic_container_id"] == "container_1"

    def test_union_references(self, material, model):
        """Test container with union references."""
        # Test with material
        container1 = UnionReferenceContainer.create(
            id="union_1",
            name="Union Container 1",
            resource=material
        )

        # Test with model
        container2 = UnionReferenceContainer.create(
            id="union_2",
            name="Union Container 2",
            resource=model
        )

        # Test references
        assert container1.resource is material
        assert container2.resource is model

        # This is a complex case - verify basic functionality works
        # but full Union handling might require additional implementation
        assert container1.entity_ids["resource"] == "material_1"
        assert container2.entity_ids["resource"] == "model_1"

    def test_self_references(self):
        """Test container with self-references."""
        # Create a parent
        parent = SelfReferenceContainer.create(
            id="parent_1",
            name="Parent Container"
        )

        # Create two children
        child1 = SelfReferenceContainer.create(
            id="child_1",
            name="Child Container 1",
            parent=parent
        )

        child2 = SelfReferenceContainer.create(
            id="child_2",
            name="Child Container 2",
            parent=parent
        )

        # Update parent with children
        parent = parent.with_changes(children=[child1, child2])

        # Test references
        assert child1.parent is parent
        assert child2.parent is parent
        assert len(parent.children) == 2
        assert parent.children[0] is child1
        assert parent.children[1] is child2

        # Test entity_ids
        assert child1.entity_ids["parent"] == "parent_1"
        assert child2.entity_ids["parent"] == "parent_1"
        # List handling isn't implemented yet
        assert "children" not in parent.entity_ids

    def test_with_changes(self, material, model):
        """Test with_changes preserves entity references and IDs."""
        container = BasicReferenceContainer.create(
            id="container_1",
            name="Original Container",
            material=material,
            model=model
        )

        # Change name and one reference
        material2 = SimpleMaterial.create(
            id="material_2",
            name="Aluminum",
            density=2700.0
        )

        updated = container.with_changes(
            name="Updated Container",
            material=material2
        )

        # Test basic properties
        assert updated.id == container.id  # ID should not change
        assert updated.name == "Updated Container"

        # Test references
        assert updated.material is material2
        assert updated.model is model  # Unchanged reference

        # Test entity_ids
        assert updated.entity_ids["material"] == "material_2"
        assert updated.entity_ids["model"] == "model_1"

    def test_unknown_entity_id(self):
        """Test getting ID for unknown entity."""
        container = BasicReferenceContainer.create(
            id="container_1",
            name="Basic Container",
            material=None,
            model=None
        )

        assert container.get_entity_id("unknown") is None

    def test_field_detection(self):
        """Test proper detection of Identifiable fields."""
        # Check that _identifiable_fields class variable is populated correctly
        assert "material" in BasicReferenceContainer._identifiable_fields
        assert "model" in BasicReferenceContainer._identifiable_fields

        # Optional fields should also be detected
        assert "material" in OptionalReferenceContainer._identifiable_fields
        assert "model" in OptionalReferenceContainer._identifiable_fields

    def test_malformed_registry(self, material, model):
        """Test behavior with malformed entity registry."""
        # Create container with only IDs
        container = BasicReferenceContainer.model_validate({
            "id": "container_1",
            "name": "Basic Container",
            "material_id": "material_1",
            "model_id": "model_1"
        })

        # Test with empty registry
        empty_registry = {}
        resolved = container.resolve_references(empty_registry)
        assert resolved.material is None
        assert resolved.model is None

        # Test with partial registry
        partial_registry = {
            "SimpleMaterial": {"material_1": material}
        }
        resolved = container.resolve_references(partial_registry)
        assert resolved.material is material
        assert resolved.model is None

        # Test with wrong ID
        wrong_registry = {
            "SimpleMaterial": {"wrong_id": material},
            "SimpleModel": {"wrong_id": model}
        }
        resolved = container.resolve_references(wrong_registry)
        assert resolved.material is None
        assert resolved.model is None

    def test_nonidentifiable_field(self):
        """Test behavior with non-Identifiable fields."""

        # Define a class with mix of Identifiable and non-Identifiable fields
        class MixedContainer(EntityReferenceContainer, Identifiable):
            name: str
            material: SimpleMaterial
            value: int  # Not an Identifiable

        container = MixedContainer.create(
            id="mixed_1",
            name="Mixed Container",
            material=SimpleMaterial.create(id="mat_1", name="Test", density=1.0),
            value=42
        )

        # Check that only Identifiable fields are in entity_ids
        assert "material" in container.entity_ids
        assert "value" not in container.entity_ids
        assert "name" not in container.entity_ids

    def test_serialization_exclusion(self, material, model):
        """Test serialization with exclusion options."""
        container = BasicReferenceContainer.create(
            id="container_1",
            name="Basic Container",
            material=material,
            model=model
        )

        # Test excluding specific fields
        serialized = container.model_dump(exclude={"material"})
        assert "material" not in serialized
        assert "material_id" not in serialized  # Should also exclude ID field
        assert "model" in serialized
        assert "model_id" in serialized

        # Test include only
        serialized = container.model_dump(include={"id", "name", "material"})
        assert "material" in serialized
        assert "material_id" in serialized
        assert "model" not in serialized
        assert "model_id" not in serialized

    def test_generic_dict_reference(self):
        """Test container with dict of identifiable objects."""

        # Create a container class with a dictionary of identifiable objects
        class DictReferenceContainer(EntityReferenceContainer, Identifiable):
            name: str
            material_map: Dict[str, SimpleMaterial]

        # Create materials
        material1 = SimpleMaterial.create(id="mat_1", name="Steel", density=7850.0)
        material2 = SimpleMaterial.create(id="mat_2", name="Aluminum", density=2700.0)

        # Create container
        container = DictReferenceContainer.create(
            id="dict_container",
            name="Dictionary Container",
            material_map={"steel": material1, "aluminum": material2}
        )

        # This is a complex case that initial implementation might not handle
        # For now, verify basic functionality
        assert container.material_map["steel"] is material1
        assert container.material_map["aluminum"] is material2

        # Serialization test - might need specialized implementation
        serialized = container.model_dump()
        assert "material_map" in serialized

        # Initial implementation might not extract IDs from dict values
        # Document expected behavior when implemented
        # assert "material_map" in container.entity_ids

    def test_nested_generic_types(self):
        """Test container with deeply nested generic types."""

        # Create a container with nested generic types
        class ComplexGenericContainer(EntityReferenceContainer, Identifiable):
            name: str
            # List of dictionaries mapping strings to optional materials
            complex_structure: List[Dict[str, Optional[SimpleMaterial]]]

        # Create test materials
        material1 = SimpleMaterial.create(id="mat_1", name="Steel", density=7850.0)
        material2 = SimpleMaterial.create(id="mat_2", name="Aluminum", density=2700.0)

        # Create a complex nested structure
        complex_structure = [
            {"steel": material1, "empty": None},
            {"aluminum": material2}
        ]

        # Create container
        container = ComplexGenericContainer.create(
            id="complex_container",
            name="Complex Container",
            complex_structure=complex_structure
        )

        # Verify the structure is preserved
        assert container.complex_structure[0]["steel"] is material1
        assert container.complex_structure[0]["empty"] is None
        assert container.complex_structure[1]["aluminum"] is material2

        # Serialization test
        serialized = container.model_dump()
        assert "complex_structure" in serialized

        # Advanced ID extraction for nested structures would need specialized implementation
        # Document expected behavior when implemented
        # assert "complex_structure" in container.entity_ids

    def test_complex_circular_references(self):
        """Test complex circular reference chains."""

        # Define classes with circular references
        class NodeA(EntityReferenceContainer, Identifiable):
            name: str
            ref_to_b: Optional["NodeB"] = None

        class NodeB(EntityReferenceContainer, Identifiable):
            name: str
            ref_to_c: Optional["NodeC"] = None

        class NodeC(EntityReferenceContainer, Identifiable):
            name: str
            ref_to_a: Optional["NodeA"] = None

        # Rebuild models for forward references
        NodeA.model_rebuild()
        NodeB.model_rebuild()
        NodeC.model_rebuild()

        # Create the nodes
        node_a = NodeA.create(id="a_1", name="Node A")
        node_b = NodeB.create(id="b_1", name="Node B")
        node_c = NodeC.create(id="c_1", name="Node C")

        # Connect them in a circular chain
        node_a = node_a.with_changes(ref_to_b=node_b)
        node_b = node_b.with_changes(ref_to_c=node_c)
        node_c = node_c.with_changes(ref_to_a=node_a)

        # Test references
        assert node_a.ref_to_b is node_b
        assert node_b.ref_to_c is node_c
        assert node_c.ref_to_a is node_a

        # Test entity_ids
        assert node_a.entity_ids["ref_to_b"] == "b_1"
        assert node_b.entity_ids["ref_to_c"] == "c_1"
        assert node_c.entity_ids["ref_to_a"] == "a_1"

        # Test serialization - should not cause infinite recursion
        a_serialized = node_a.model_dump()
        b_serialized = node_b.model_dump()
        c_serialized = node_c.model_dump()

        assert a_serialized["ref_to_b_id"] == "b_1"
        assert b_serialized["ref_to_c_id"] == "c_1"
        assert c_serialized["ref_to_a_id"] == "a_1"

        # Test deserialization and resolution
        # Create serialized data with just IDs
        a_data = {"id": "a_1", "name": "Node A", "ref_to_b_id": "b_1"}
        b_data = {"id": "b_1", "name": "Node B", "ref_to_c_id": "c_1"}
        c_data = {"id": "c_1", "name": "Node C", "ref_to_a_id": "a_1"}

        # Deserialize
        a_deserialized = NodeA.model_validate(a_data)
        b_deserialized = NodeB.model_validate(b_data)
        c_deserialized = NodeC.model_validate(c_data)

        # Check IDs were extracted
        assert a_deserialized.get_entity_id("ref_to_b") == "b_1"
        assert b_deserialized.get_entity_id("ref_to_c") == "c_1"
        assert c_deserialized.get_entity_id("ref_to_a") == "a_1"

        # Set up registry
        registry = {
            "NodeA": {"a_1": a_deserialized},
            "NodeB": {"b_1": b_deserialized},
            "NodeC": {"c_1": c_deserialized}
        }

        # Resolve references
        a_resolved = a_deserialized.resolve_references(registry)
        b_resolved = b_deserialized.resolve_references(registry)
        c_resolved = c_deserialized.resolve_references(registry)

        # This might cause infinite recursion without proper handling
        # Verify references are resolved correctly
        assert a_resolved.ref_to_b is b_deserialized
        assert b_resolved.ref_to_c is c_deserialized
        assert c_resolved.ref_to_a is a_deserialized

    def test_type_variable_handling(self):
        """Test handling of type variables and generics."""
        from typing import TypeVar, Generic

        T = TypeVar('T', bound=Identifiable)

        # Define a generic container
        class GenericContainer(EntityReferenceContainer, Identifiable, Generic[T]):
            name: str
            item: T

        # Use with different Identifiable types
        material_container = GenericContainer[SimpleMaterial].create(
            id="container_1",
            name="Material Container",
            item=SimpleMaterial.create(id="mat_1", name="Steel", density=7850.0)
        )

        model_container = GenericContainer[SimpleModel].create(
            id="container_2",
            name="Model Container",
            item=SimpleModel.create(id="mod_1", name="Linear", parameter=1.0)
        )

        # Test references
        assert material_container.item.id == "mat_1"
        assert model_container.item.id == "mod_1"

        # Test entity_ids
        assert material_container.entity_ids["item"] == "mat_1"
        assert model_container.entity_ids["item"] == "mod_1"

        # Test serialization
        mat_serialized = material_container.model_dump()
        mod_serialized = model_container.model_dump()

        assert mat_serialized["item_id"] == "mat_1"
        assert mod_serialized["item_id"] == "mod_1"

    def test_inheritance_of_identifiable_fields(self):
        """Test that Identifiable fields are properly detected in inherited classes."""

        # Base class with Identifiable fields
        class BaseContainer(EntityReferenceContainer, Identifiable):
            name: str
            base_material: SimpleMaterial

        # Derived class with additional Identifiable fields
        class DerivedContainer(BaseContainer):
            derived_model: SimpleModel

        # Create instance
        container = DerivedContainer.create(
            id="derived_1",
            name="Derived Container",
            base_material=SimpleMaterial.create(id="mat_1", name="Steel", density=7850.0),
            derived_model=SimpleModel.create(id="mod_1", name="Linear", parameter=1.0)
        )

        # Check field detection (both base and derived fields should be detected)
        assert "base_material" in DerivedContainer._identifiable_fields
        assert "derived_model" in DerivedContainer._identifiable_fields

        # Check entity_ids
        assert container.entity_ids["base_material"] == "mat_1"
        assert container.entity_ids["derived_model"] == "mod_1"

        # Check serialization
        serialized = container.model_dump()
        assert serialized["base_material_id"] == "mat_1"
        assert serialized["derived_model_id"] == "mod_1"

    def test_interface_extensibility(self):
        """Test that EntityReferenceContainer interface can be extended."""

        # Create an extended container with additional reference handling methods
        class ExtendedContainer(EntityReferenceContainer, Identifiable):
            name: str
            material: SimpleMaterial

            def get_entity_type(self, field_name: str) -> Optional[str]:
                """Get the type name of an entity field."""
                if field_name in self._identifiable_fields:
                    entity = getattr(self, field_name, None)
                    if entity is not None:
                        return entity.__class__.__name__
                return None

        # Create instance
        material = SimpleMaterial.create(id="mat_1", name="Steel", density=7850.0)
        container = ExtendedContainer.create(
            id="ext_1",
            name="Extended Container",
            material=material
        )

        # Test extended functionality
        assert container.get_entity_type("material") == "SimpleMaterial"
        assert container.get_entity_type("name") is None

        # Ensure original functionality still works
        assert container.entity_ids["material"] == "mat_1"
        assert container.get_entity_id("material") == "mat_1"
