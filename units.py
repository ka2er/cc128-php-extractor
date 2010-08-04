# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Simple handling of physical quantities with units."""

units_by_symbol = {}


class Unit(object):
  """An instance of this class represents a unit of measurement.

  Internally, each unit is represented as a numerical conversion factor and
  a reference to a base unit, e.g. KILOWATT has factor 1000 and base WATT.
  """

  def __init__(self, symbol, factor=1, base=None, factorizations=()):
    self.symbol = symbol
    self.factor = factor
    self.base = base or self
    if self.base is self:
      assert self.factor == 1
    self.products = {}
    self.quotients = {}
    for left, right in factorizations:
      self.quotients[left] = right
      self.quotients[right] = left
      left.products[right] = self
      right.products[left] = self
    units_by_symbol[symbol] = self

  def __str__(self):
    return self.symbol

  def __repr__(self):
    return '<Unit: %s>' % self

  def __rmul__(self, other):
    return Quantity(other, self)

  def __mul__(self, other):
    if isinstance(other, Unit):
      return self.products[other]
    return other*self

  def __div__(self, other):
    return self.quotients[other]

  def IsConvertibleTo(self, unit):
    """Returns True if this unit can be converted to the given unit."""
    return unit.base is self.base


class Quantity(object):
  """A physical quantity (consisting of a numerical value and a unit)."""

  def __init__(self, value, unit):
    self.value = float(value)
    self.unit = unit

  def __eq__(self, other):
    if isinstance(other, Quantity):
      return (self.value, self.unit) == (other.value, other.unit)

  def __str__(self):
    return '%g %s' % (self.value, self.unit)

  def __repr__(self):
    return '<Quantity: %s>' % self

  def __neg__(self):
    return Quantity(-self.value, self.unit)

  def __add__(self, other):
    other = other.ConvertTo(self.unit)
    return Quantity(self.value + other.value, self.unit)

  def __sub__(self, other):
    other = other.ConvertTo(self.unit)
    return Quantity(self.value - other.value, self.unit)

  def __div__(self, other):
    if isinstance(other, Unit):
      if other in self.unit.quotients:
        return Quantity(self.value, self.unit / other)
    elif isinstance(other, Quantity):
      if other.unit in self.unit.quotients:
        return Quantity(self.value / other.value, self.unit / other.unit)
      if other.unit is self.unit:
        return self.value / other.value
    return self.ConvertTo(self.unit.base) / other

  def __mul__(self, other):
    if isinstance(other, (int, float)):
      # Multiply this quantity by a scalar.
      return Quantity(self.value * other, self.unit)
    elif isinstance(other, Unit):
      # Multiply this quantity by a unit.
      if other in self.unit.products:
        return Quantity(self.value, self.unit * other)
    elif isinstance(other, Quantity):
      # Multiply this quantity by another quantity.
      if other.unit in self.unit.products:
        return Quantity(self.value * other.value, self.unit * other.unit)

  def __rmul__(self, other):
    return self*other

  def ConvertTo(self, unit):
    """Converts this value to a given unit."""
    assert self.unit.IsConvertibleTo(unit)
    return Quantity(self.value * self.unit.factor / unit.factor, unit)

  def IsConvertibleTo(self, unit):
    """Returns True if this quantity can be converted to the given unit."""
    return self.unit.IsConvertibleTo(unit)


# Basic units for electrical energy.
# TODO(kpy): Units and quantities still don't multiply properly.

SECOND = Unit('s')
WATT = Unit('W')
JOULE = Unit('J', factorizations=[(WATT, SECOND)])  # J = W * s
KILOWATT_HOUR = Unit('kW h', 3600*1000, JOULE)

MINUTE = 60*SECOND
HOUR = 60*MINUTE
KILOWATT = 1000*WATT
MEGAWATT = 1000*KILOWATT
