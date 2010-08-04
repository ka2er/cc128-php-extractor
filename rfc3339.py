# Copyright 2009 Google Inc.
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

"""Conversions to and from RFC 3339 timestamp format."""

import calendar
import re
import time


def ToTimestamp(unix_time):
  """Converts a Unix time to an RFC 3339 timestamp in UTC.
  Note that fractions less than a millisecond are truncated.

  Args:
    unix_time: seconds (int or float) since January 1, 1970, 00:00:00 UTC
  Returns:
    a timestamp in RFC 3339 format (yyyy-mm-ddThh:mm:ss.sssZ)
  """
  year, month, day, hour, minute, second = time.gmtime(unix_time)[:6]
  milliseconds = int(unix_time * 1000) - (int(unix_time) * 1000)
  return '%04d-%02d-%02dT%02d:%02d:%02d.%03dZ' % (
      year, month, day, hour, minute, second, milliseconds)


def ToTimestampWithZone(unix_time, offset_hours):
  """Converts a Unix time to an RFC 3339 timestamp with a time zone offset.
  Note that fractions less than a millisecond are truncated.  The offset
  should be specified in hours east of UTC.

  Args:
    unix_time: seconds (int or float) since January 1, 1970, 00:00:00 UTC
  Returns:
    a timestamp in RFC 3339 format (yyyy-mm-ddThh:mm:ss.sss[+-]hh:mm)
  """
  offset_time = unix_time + offset_hours * 3600
  zone_sign = (offset_hours < 0) and '-' or '+'
  zone_minutes = abs(offset_hours) * 60
  return ToTimestamp(offset_time).replace(
      'Z', '%s%02d:%02d' % (zone_sign, zone_minutes / 60, zone_minutes % 60))


def FromTimestamp(timestamp):
  """Converts an RFC 3339 timestamp to Unix time in seconds since the epoch.
  The result is always an integer multiple of 0.001; fractions less than a
  millisecond are truncated.

  Args:
    timestamp: a timestamp in RFC 3339 format (yyyy-mm-ddThh:mm:ss.sss
        followed by a time zone, given as Z, +hh:mm, or -hh:mm)
  Returns:
    a number of seconds since January 1, 1970, 00:00:00 UTC
  Raises:
    ValueError: if the timestamp is not in an acceptable format
  """
  # Remove any whitespace in the timestamp.
  timestamp = ''.join(timestamp.split())

  match = re.match(r'(\d\d\d\d)-(\d\d)-(\d\d)T(\d\d):(\d\d)(?::(\d\d\.?\d*))?'
                   r'(Z|[-+]\d+:?(\d\d)?)', timestamp)
  if not match:
    raise ValueError('not a valid timestamp: %r' % timestamp)
  year, month, day, hour, minute, second, zone, zone_minutes = match.groups()

  # Parse the fractional seconds separately to avoid floating-point errors,
  # e.g. 32 + 0.001 == 32.000999999999998 != 32001 * 0.001.
  int_second = (second or '0').split('.')[0]
  milliseconds = 0
  if second and '.' in second:
    milliseconds = int((second.split('.')[1] + '000')[:3])
  time_tuple = map(int, [year, month, day, hour, minute, int_second])

  # Parse the time zone offset.
  if zone[0] == 'Z':
    zone_offset = 0
  else:
    zone_hours = zone[1:].split(':')[0]
    zone_offset = int(zone_hours) * 3600 + int(zone_minutes or 0) * 60
    if zone[0] == '-':
      zone_offset = -zone_offset

  integer_time = calendar.timegm(time_tuple) - zone_offset
  return (integer_time * 1000 + milliseconds) * 0.001
