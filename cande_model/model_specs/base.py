# In CANDE layer
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
from pydantic import BaseModel, Field, field_validator
import pint

ureg = pint.UnitRegistry()


class CandeParameterSpec:
    """Descriptor for CANDE parameter specifications."""

    def __init__(self,
                 required_unit: str,
                 validation_rules: Optional[Dict] = None,
                 description: Optional[str] = None):
        self.required_unit = required_unit
        self.validation_rules = validation_rules or {}
        self.description = description
        self._name = None

    def __set_name__(self, owner, name):
        self._name = name

    def extract_value(self, param: Parameter) -> float:
        """Extract and convert a single parameter value."""
        # Validate
        self._validate(param.value)

        # Convert using pint
        if param.unit and param.unit != self.required_unit:
            quantity = param.value * ureg(param.unit)
            converted = quantity.to(self.required_unit)
            return converted.magnitude

        return param.value

    def _validate(self, value: float):
        """Validate parameter value against rules."""
        if "min" in self.validation_rules and value < self.validation_rules["min"]:
            raise ValueError(f"{self._name} must be >= {self.validation_rules['min']}")
        if "max" in self.validation_rules and value > self.validation_rules["max"]:
            raise ValueError(f"{self._name} must be <= {self.validation_rules['max']}")

    def __get__(self, instance, owner):
        """Allow accessing the spec itself via the class."""
        return self


class CandeSoilModelSpec(BaseModel, ABC):
    """Base class for CANDE soil model specifications."""

    model_config = {
        "arbitrary_types_allowed": True,  # Allows descriptors
    }

    @property
    def parameter_specs(self) -> Dict[str, CandeParameterSpec]:
        """Collect all CandeParameterSpec descriptors."""
        specs = {}
        for name in dir(self):
            attr = getattr(type(self), name, None)
            if isinstance(attr, CandeParameterSpec):
                specs[name] = attr
        return specs

    def extract_values(self, domain_params: ModelParameters) -> Dict[str, float]:
        """Extract all parameter values in CANDE units."""
        values = {}
        for name, spec in self.parameter_specs.items():
            param = domain_params.get_parameter(name)
            if param is None:
                raise ValueError(f"Missing required parameter: {name}")
            values[name] = spec.extract_value(param)
        return values

    @classmethod
    def get_parameter_info(cls) -> Dict[str, Dict[str, Any]]:
        """Get information about all parameters for serialization."""
        info = {}
        for name in dir(cls):
            attr = getattr(cls, name, None)
            if isinstance(attr, CandeParameterSpec):
                info[name] = {
                    "required_unit": attr.required_unit,
                    "validation_rules": attr.validation_rules,
                    "description": attr.description
                }
        return info


# Concrete implementation
class DuncanSeligSpec(CandeSoilModelSpec):
    """Duncan-Selig hyperbolic soil model specification."""

    # Class-level descriptors
    K = CandeParameterSpec("psi", validation_rules={"min": 0})
    n = CandeParameterSpec("", validation_rules={"min": 0})
    Rf = CandeParameterSpec("", validation_rules={"min": 0, "max": 1})
    c = CandeParameterSpec("psi", validation_rules={"min": 0})
    phi = CandeParameterSpec("degree", validation_rules={"min": 0, "max": 90})
    K_b = CandeParameterSpec("psi", validation_rules={"min": 0})
    m = CandeParameterSpec("", validation_rules={"min": 0})
    D = CandeParameterSpec("psi", validation_rules={"min": 0})

    # Pydantic fields can be added if needed
    model_name: str = Field(default="Duncan-Selig")
    model_type: str = Field(default="hyperbolic")


# Serialization works!
spec = DuncanSeligSpec()
print(spec.model_dump())  # Serializes Pydantic fields

# Get parameter info for documentation/UI
param_info = DuncanSeligSpec.get_parameter_info()
print(param_info)  # All parameter specifications

# Usage remains the same
cande_values = spec.extract_values(domain_params)
