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

"""A simple client library for the Google Meter API.

To post a single measurement event:
  - Create a Service object (passing in a valid AuthSub token).
  - Create a Variable object (specifying at least the user ID, provider
    domain, and variable ID).
  - Create an InstMeasurement object with the desired values.
  - Call the service's PostEvent method on the InstMeasurement object.

To batch-post events, create a Service object and call BatchPostEvents on
a list of event objects.

To retrieve entities and events, create a Service object and call GetEntity,
GetEntities, GetEvent, or GetEvents.
"""

import posixpath
import re
import socket
import sys
import time
import urllib
import urlparse
import xml.sax

import rfc3339
import units


# The location of the standard Google Meter service.
DEFAULT_URI_PREFIX = 'https://www.google.com/powermeter/feeds'

# Max number of events we'll post at a time.
MAX_BATCH_POST_COUNT = 100

# XML namespace attributes for the Google Meter API.
XMLNS_ATTRIBUTES = (' xmlns="http://www.w3.org/2005/Atom"'
                    ' xmlns:meter="http://schemas.google.com/meter/2008"')


def HtmlEscape(text):
  """Escapes plain text for safe transmission in HTML or XML."""
  return text.replace('&', '&amp;').replace('<', '&lt;').replace('"', '&quot;')


def IncludeIfTrue(flag, string):
  """Returns the given string or an empty string, depending on the flag."""
  if flag:
    return string
  return ''


def GetEntityPath(entity_or_path):
  """Given an Entity object or a path string, returns the path."""
  if isinstance(entity_or_path, Entity):
    return entity_or_path.path
  else:
    return entity_or_path


def GetAtomId(entity_or_path):
  """Gets the Atom ID for a given entity path or Entity object."""
  # The Atom ID always starts with the canonical URI prefix, regardless
  # of the URI being used to contact the Google Meter service.
  return DEFAULT_URI_PREFIX + GetEntityPath(entity_or_path)


def GetPathComponents(uri_or_path):
  """Gets a list of the path components from the given path or URI."""
  if uri_or_path.startswith(DEFAULT_URI_PREFIX):
    path = uri_or_path[len(DEFAULT_URI_PREFIX):]
  else:
    path = uri_or_path
  return path.lstrip('/').split('/')


def ParseEntries(content):
  """Parses any <entry> elements in the given XML document into a list of
  entity or event objects."""
  handler = GdataHandler()
  xml.sax.parseString(content, handler)
  results = []
  for entry in handler.entries:
    # Extract fields that are common to multiple entry kinds.
    entry_path = GetPathComponents(entry['id'])
    kind, id = entry_path[-2:]
    if 'meter:subject' in entry:
      subject_path = '/' + '/'.join(entry_path[:-2])
    if 'meter:quantity' in entry:
      unit = units.units_by_symbol[entry['meter:quantity/meter:unit']]
      quantity = float(entry['meter:quantity'].strip()) * unit
      uncertainty = float(entry['meter:quantity/meter:uncertainty']) * unit

    # Construct the entity or event appropriate for the entry kind.
    if kind == 'variable':
      user_id, zone = entry_path[1:3]
      results.append(Variable(
          user_id, zone, id, entry['title'], entry['content'],
          entry['meter:location'], entry['meter:type'], entry['meter:unit'],
          'meter:cumulative' in entry, 'meter:durational' in entry))
    elif kind == 'messageStream':
      # messageStreams are only available to utility providers
      provider_domain = entry['id'].split('/')[-3]
      results.append(MessageStream(
          provider_domain, id, entry['title'], entry['content']))
    elif kind == 'durMeasurement':
      results.append(DurMeasurement(
          subject_path, rfc3339.FromTimestamp(entry['meter:startTime']),
          rfc3339.FromTimestamp(entry['meter:endTime']), quantity,
          float(entry['meter:startTime/meter:uncertainty'].strip()),
          float(entry['meter:endTime/meter:uncertainty'].strip()), uncertainty))
    elif kind == 'durMessage':
      # messageStreams are only available to utility providers
      results.append(DurMessage(
          subject_path, rfc3339.FromTimestamp(entry['meter:startTime']),
          rfc3339.FromTimestamp(entry['meter:endTime']),
          entry['title'], entry['content'], entry.get('link/href', None)))
    elif kind == 'instMeasurement':
      results.append(InstMeasurement(
          subject_path, rfc3339.FromTimestamp(entry['meter:occurTime']),
          quantity, float(entry['meter:occurTime/meter:uncertainty'].strip()),
          uncertainty, 'meter:initial' in entry))
  return results


class GdataHandler(xml.sax.ContentHandler):
  """A simple SAX ContentHandler that turns the contents of each <entry>
  element into a flat dictionary of key-value pairs.  Each child element
  becomes a key in the dictionary, with its character content as the value.
  Each attribute of a child element becomes another key in the dictionary
  in the form "element/attribute", with the attribute value as the value.
  After parsing, the list of dictionaries is available in self.entries."""

  def __init__(self):
    self.entries = []
    self.field = None
    self.entry = None
    self.content = ''

  def startElement(self, name, attrs):
    if self.entry is not None:  # element inside an <entry>
      self.field = name
      self.content = ''
      if name == 'link' and attrs['rel'] != 'related':
        return  # only <link rel="related"> matters for us
      for key in attrs.keys():
        self.entry[name + '/' + key] = attrs[key]
    elif name == 'entry':  # start of a new <entry>
      self.entry = {}

  def characters(self, content):
    self.content += content

  def endElement(self, name):
    if name == 'entry':  # end of an <entry>
      self.entries.append(self.entry)
      self.entry = None
    elif name == self.field:  # end of an element inside an <entry>
      self.entry[self.field] = self.content


class Log(object):
  """A logging service with a configurable level of detail."""

  def __init__(self, level=1, outfile=sys.stderr):
    """Creates an instance of the logging service.

    Args:
      level: a number indicating the logging level (higher means more messages)
      outfile: a file object to which log messages will be written
    """
    self.level = level
    self.outfile = outfile

  def Log(self, level, message):
    """Writes out a log message if its level is low enough for this Log."""
    if self.level >= level:
      self.outfile.write(message + '\n')
      self.outfile.flush()


class InstMeasurement(object):
  """An instantaneous measurement event."""
  kind = 'instMeasurement'

  def __init__(self, subject, occur_time, quantity,
               occur_time_uncertainty, quantity_uncertainty, initial=False):
    """Creates a instantaneous measurement event.

    Args:
      subject: an entity path or Entity object for the subject of this event
      occur_time: the time of the measurement in seconds since the epoch
      quantity: the measured quantity as a Quantity object
      occur_time_uncertainty: the uncertainty in occur_time, in seconds
      quantity_uncertainty: the measurement uncertainty as a Quantity object
      initial: a flag, true if a meter reset preceded this measurement
    """
    self.subject_path = GetEntityPath(subject)
    self.occur_time = occur_time
    self.quantity = quantity
    self.occur_time_uncertainty = occur_time_uncertainty
    self.quantity_uncertainty = quantity_uncertainty
    self.initial = initial
    self.id = rfc3339.ToTimestamp(self.occur_time).replace(':', '_')

  def __str__(self):
    return '%s: %s%s' % (rfc3339.ToTimestamp(self.occur_time), self.quantity,
        IncludeIfTrue(self.initial, ' (initial)'))

  def __repr__(self):
    return 'InstMeasurement(%r, %s, %r, %s, %r, %r)' % (
        self.subject_path, self.occur_time, self.quantity,
        self.occur_time_uncertainty, self.quantity_uncertainty, self.initial)

  def __eq__(self, other):
    if isinstance(other, InstMeasurement):
      return [
          self.subject_path, self.occur_time, self.quantity,
          self.occur_time_uncertainty, self.quantity_uncertainty,
          self.initial
      ] == [
          other.subject_path, other.occur_time, other.quantity,
          other.occur_time_uncertainty, other.quantity_uncertainty,
          other.initial
      ]

  def ToXml(self):
    """Produces the XML <entry> element for this event."""
    return '''
<entry%s>
  <id>%s</id>
  <category scheme="http://schemas.google.com/g/2005#kind"
            term="http://schemas.google.com/meter/2008#instMeasurement"/>
  <meter:subject>%s</meter:subject>
  <meter:occurTime meter:uncertainty="%f">%s</meter:occurTime>
  <meter:quantity meter:uncertainty="%f" meter:unit="kW h">
    %f
  </meter:quantity>
%s</entry>
''' % (XMLNS_ATTRIBUTES,
       GetAtomId(self.subject_path + '/' + self.kind + '/' + self.id),
       GetAtomId(self.subject_path),
       self.occur_time_uncertainty,
       rfc3339.ToTimestamp(self.occur_time),
       self.quantity_uncertainty.ConvertTo(units.KILOWATT_HOUR).value,
       self.quantity.ConvertTo(units.KILOWATT_HOUR).value,
       IncludeIfTrue(self.initial, '  <meter:initial/>\n'))


class DurMeasurement(object):
  """An durational measurement event."""
  kind = 'durMeasurement'

  def __init__(self, subject, start_time, end_time, quantity,
               start_time_uncertainty, end_time_uncertainty,
               quantity_uncertainty):
    """Creates a durational measurement event.

    Args:
      subject: an entity path or Entity object for the subject of this event
      start_time: the start of the measured interval in seconds since the epoch
      end_time: the end of the measured interval in seconds since the epoch
      quantity: the measured quantity as a Quantity object
      start_time_uncertainty: the uncertainty in start_time, in seconds
      end_time_uncertainty: the uncertainty in end_time, in seconds
      quantity_uncertainty: the measurement uncertainty as a Quantity object
    """
    self.subject_path = GetEntityPath(subject)
    self.start_time = start_time
    self.end_time = end_time
    self.quantity = quantity
    self.start_time_uncertainty = start_time_uncertainty
    self.end_time_uncertainty = end_time_uncertainty
    self.quantity_uncertainty = quantity_uncertainty
    self.id = rfc3339.ToTimestamp(self.start_time).replace(':', '_')

  def __str__(self):
    return '%s to %s: %s' % (rfc3339.ToTimestamp(self.start_time),
        rfc3339.ToTimestamp(self.end_time), self.quantity)

  def __repr__(self):
    return 'DurMeasurement(%r, %s, %s, %r, %s, %s, %r)' % (
        self.subject_path, self.start_time, self.end_time, self.quantity,
        self.start_time_uncertainty, self.end_time_uncertainty,
        self.quantity_uncertainty)

  def __eq__(self, other):
    if isinstance(other, DurMeasurement):
      return [
          self.subject_path, self.start_time, self.end_time, self.quantity,
          self.start_time_uncertainty, self.end_time_uncertainty,
          self.quantity_uncertainty
      ] == [
          other.subject_path, other.start_time, other.end_time, other.quantity,
          other.start_time_uncertainty, other.end_time_uncertainty,
          other.quantity_uncertainty
      ]

  def ToXml(self):
    """Produces the XML <entry> element for this event."""
    return '''
<entry%s>
  <id>%s</id>
  <category scheme="http://schemas.google.com/g/2005#kind"
            term="http://schemas.google.com/meter/2008#durMeasurement"/>
  <meter:subject>%s</meter:subject>
  <meter:startTime meter:uncertainty="%f">%s</meter:startTime>
  <meter:endTime meter:uncertainty="%f">%s</meter:endTime>
  <meter:quantity meter:uncertainty="%f" meter:unit="kW h">
    %f
  </meter:quantity>
</entry>
''' % (XMLNS_ATTRIBUTES,
       GetAtomId(self.subject_path + '/' + self.kind + '/' + self.id),
       GetAtomId(self.subject_path),
       self.start_time_uncertainty,
       rfc3339.ToTimestamp(self.start_time),
       self.end_time_uncertainty,
       rfc3339.ToTimestamp(self.end_time),
       self.quantity_uncertainty.ConvertTo(units.KILOWATT_HOUR).value,
       self.quantity.ConvertTo(units.KILOWATT_HOUR).value)


class DurMessage(object):
  """A durational message event.
     Durational message events are only available to utility providers
     at the moment.
  """
  kind = 'durMessage'

  def __init__(self, subject, start_time, end_time, title, content,
               link=None, priority=0):
    """Creates a durational message event.

    Args:
      subject: an entity path or Entity object for the subject of this event
      start_time: the starting time of the message in seconds since the epoch
      end_time: the ending time of the message in seconds since the epoch
      title: the title of the message in plain text
      content: the content of the message in plain text
      link: an optional URL for a link to show with the message
      priority: optional priority, an integer > 0.
    """
    self.subject_path = GetEntityPath(subject)
    self.start_time = start_time
    self.start_time_uncertainty = 0
    self.end_time = end_time
    self.end_time_uncertainty = 0
    self.title = title
    self.content = content
    self.link = link
    self.id = rfc3339.ToTimestamp(self.start_time).replace(':', '_')
    self.priority = priority

  def __str__(self):
    return '%s to %s: %r%s, priority: %s' % (
        rfc3339.ToTimestamp(self.start_time),
        rfc3339.ToTimestamp(self.end_time), self.content,
        IncludeIfTrue(self.link, ' (link: %r)' % self.link), self.priority)

  def __repr__(self):
    return 'DurMessage(%r, %s, %s, %r, %r, %r, %s)' % (
        self.subject_path, self.start_time, self.end_time,
        self.title, self.content, self.link, self.priority)

  def __eq__(self, other):
    if isinstance(other, DurMessage):
      return [
          self.subject_path, self.start_time, self.start_time_uncertainty,
          self.end_time, self.end_time_uncertainty,
          self.title, self.content, self.link, self.priority
      ] == [
          other.subject_path, other.start_time, other.start_time_uncertainty,
          other.end_time, other.end_time_uncertainty,
          other.title, other.content, other.link, other.priority
      ]

  def ToXml(self):
    """Generates the XML <entry> element for this event."""
    return '''
<entry%s>
  <id>%s</id>
  <category scheme="http://schemas.google.com/g/2005#kind"
            term="http://schemas.google.com/meter/2008#durMessage"/>
  <meter:subject>%s</meter:subject>
  <meter:startTime meter:uncertainty="0">%s</meter:startTime>
  <meter:endTime meter:uncertainty="0">%s</meter:endTime>
  <meter:priority>%s</meter:priority>
  <title type="text">%s</title>
  <content type="text">%s</content>
%s</entry>
''' % (XMLNS_ATTRIBUTES,
       GetAtomId(self.subject_path + '/' + self.kind + '/' + self.id),
       GetAtomId(self.subject_path),
       rfc3339.ToTimestamp(self.start_time),
       rfc3339.ToTimestamp(self.end_time),
       self.priority,
       HtmlEscape(self.title),
       HtmlEscape(self.content),
       IncludeIfTrue(self.link, '  <link rel="related" href="%s"/>\n' %
                     HtmlEscape(self.link or '')))


class Entity(object):
  """Abstract base class for entities; don't instantiate."""

  def __init__(self, path):
    self.path = path
    self.feed_path = posixpath.dirname(path)  # the parent of the entity path
    self.id = posixpath.basename(path)  # the last component of the entity path

  def __repr__(self):
    return '<%s at %s>' % (self.__class__.__name__, self.path)


class Variable(Entity):
  """A variable entity that can be posted to the Google Meter API."""

  def __init__(self, user_id, provider_domain, variable_id,
               name, text, location, type, unit, cumulative, durational):
    """Creates a variable object.

    Args:
      user_id: the owner's Google Meter User ID (a string of 20 decimal digits)
      provider_domain: the highest-level domain name of the provider
      variable_id: the identifier for this variable
      name: the human-readable name of this variable
      text: a human-readable description of this variable
      location: a description of the variable's location
      type: the variable's type (e.g. 'electricity_consumption')
      unit: a Unit object representing the unit of measurement
      cumulative: a flag indicating whether the measurements are cumulative
      durational: a flag indicating whether all measurements are durational
          (if false, all measurements must be instantaneous)
    """
    self.user_id = user_id
    self.zone = provider_domain
    self.id = variable_id
    self.name = name
    self.text = text
    self.location = location
    self.type = type
    self.unit = unit
    self.cumulative = cumulative
    self.durational = durational
    Entity.__init__(
        self, '/user/%s/%s/variable/%s' % (user_id, self.zone, self.id))

  def __eq__(self, other):
    if isinstance(other, Variable):
      return [
          self.user_id, self.zone, self.id,
          self.name, self.text, self.location,
          self.type, self.unit, self.cumulative, self.durational
      ] == [
          other.user_id, other.zone, other.id,
          other.name, other.text, other.location,
          other.type, other.unit, other.cumulative, other.durational
      ]

  def ToXml(self):
    """Produces the XML <entry> element for this entity."""
    return '''
<entry%s>
  <id>%s</id>
  <meter:variableId>%s</meter:variableId>
  <title>%s</title>
  <content type="text">%s</content>
  <meter:location>%s</meter:location>
  <meter:type>%s</meter:type>
  <meter:unit>%s</meter:unit>
%s%s</entry>
''' % (XMLNS_ATTRIBUTES,
       GetAtomId(self.path), self.id, self.name, self.text,
       self.location, self.type, self.unit,
       IncludeIfTrue(self.cumulative, '  <meter:cumulative/>\n'),
       IncludeIfTrue(self.durational, '  <meter:durational/>\n'))


class MessageStream(Entity):
  """A message stream entity that can be posted to the Google Meter API.
     Message streams are only available to utility providers at the moment.
  """

  def __init__(self, provider_domain, message_stream_id, name, text):
    """Creates a message stream object.

    Args:
      provider_domain: the highest-level domain name of the provider
      message_stream_id: the identifier for this message stream
      name: the human-readable name of this message stream
      text: a human-readable description of this message stream
    """
    self.provider_domain = provider_domain
    self.id = message_stream_id
    self.name = name
    self.text = text
    Entity.__init__(
        self, '/provider/%s/messageStream/%s' % (provider_domain, self.id))

  def __eq__(self, other):
    if isinstance(other, MessageStream):
      return [
          self.provider_domain, self.id, self.name, self.text
      ] == [
          other.provider_domain, other.id, other.name, other.text
      ]

  def ToXml(self):
    """Produces the XML <entry> element for this entity."""
    return '''
<entry%s>
  <id>%s</id>
  <meter:messageStreamId>%s</meter:messageStreamId>
  <title>%s</title>
  <content type="text">%s</content>
</entry>
''' % (XMLNS_ATTRIBUTES, GetAtomId(self.path), self.id, self.name, self.text)


class Service(object):
  """Authenticated access to a Google Meter service."""

  def __init__(self, token, uri_prefix=DEFAULT_URI_PREFIX, log=Log()):
    """Sets up access to a service that provides the Google Meter API.

    Args:
      token: AuthSub token to use for all requests
      uri_prefix: URI prefix under which feeds are located
      log: Log object to which messages will be logged
    """
    self.token = token
    self.scheme, hostport, self.path, _, _, _ = urlparse.urlparse(uri_prefix)
    default_port = {'http': 80, 'https': 443}[self.scheme]
    self.host, self.port = urllib.splitnport(hostport, default_port)
    self.log = log

  def __str__(self):
    return '%s:%d' % (self.host, self.port)

  def __repr__(self):
    return '<Google Meter service at %s:%d>' % (self.host, self.port)

  def Request(self, request):
    """Connects and sends a single HTTP request."""
    self.log.Log(2, '=== sending to %s:%d ===\n%s\n=== end of request ===\n' %
                 (self.host, self.port, request))
    
    # Get a file object for an appropriate socket (with or without SSL).
    sock = socket.socket()
    sock.connect((self.host, self.port))
    if self.scheme == 'https':
      sockfile = socket.ssl(sock)
    else:
      sockfile = sock.makefile()

    # Send the HTTP request.
    sockfile.write(request)
    if hasattr(sockfile, 'flush'):
      sockfile.flush()

    # Read back the entire reply.
    reply = []
    try:
      while reply[-1:] != ['']:
        reply.append(sockfile.read())
    except socket.error, e:
      # Usually SSL_ERROR_EOF just means we reached end-of-file.
      if e.args[0] != socket.SSL_ERROR_EOF:
        raise
    reply = ''.join(reply)
    self.log.Log(2, '--- reply from %s:%d ---\n%s\n--- end of reply ---\n' %
                 (self.host, self.port, reply))
    sock.close()

    # Check the status code in the reply.
    status = reply.split('\n', 1)[0].strip()
    if not re.search(r' 2\d\d ', status):
      raise IOError(status)

    # Return the content in the reply.
    match = re.search('\n\r?\n', reply)
    if match:
      return reply[match.end():]

  def Post(self, path, content):
    """Connects and sends a single HTTP POST request."""
    self.Request('''
POST %s HTTP/1.0
Host: %s
Authorization: AuthSub token="%s"
Content-Type: application/atom+xml
Content-Length: %d

%s
'''.lstrip() % (self.path + path, self.host, self.token, len(content), content))

  def PostXml(self, path, element):
    """Posts a single XML element to this service."""
    self.Post(path, '<?xml version="1.0"?>\n%s' % element.lstrip())

  def PostEntity(self, entity):
    """Posts an entity to this service."""
    self.PostXml(entity.feed_path, entity.ToXml())
    self.log.Log(1, '%s <- %r' % (self, entity))

  def PostEvent(self, event):
    """Posts a single event to this service."""
    self.PostXml(event.subject_path + '/' + event.kind, event.ToXml())
    self.log.Log(1, '%s <- %s' % (self, event))

  def BatchPostEvents(self, events):
    """Batch upload a list of usage events."""
    event_list = list(events)  # make a copy, since we'll mutate it

    # We can only upload MAX_BATCH_POST_COUNT at a time.
    while event_list:
      sublist = event_list[0:MAX_BATCH_POST_COUNT]
      event_list = event_list[MAX_BATCH_POST_COUNT:]

      entries = ''.join(event.ToXml() for event in sublist)
      feed = '<feed%s>%s</feed>' % (XMLNS_ATTRIBUTES, entries)
      self.PostXml('/event', feed)
      self.log.Log(1, '%s <- batch-posted %d events\n' %
                   (self, len(sublist)))

  def Get(self, path):
    """Connects and sends a single HTTP GET request."""
    return self.Request('''
GET %s HTTP/1.0
Host: %s
Authorization: AuthSub token="%s"

'''.lstrip() % (self.path + path, self.host, self.token))

  def GetEntity(self, path):
    """Retrieves a single entity.

    Args:
      path: the entity path (this path should have the entity type and
          entity ID as its last two components)
    """
    return ParseEntries(self.Get(path))[0]

  def GetEntities(self, path):
    """Retrieves a list of entities under a given path.

    Args:
      path: the parent path of the entities to be retrieved (this path should
          have the entity type as its last component)
    """
    return ParseEntries(self.Get(path))

  def GetEvent(self, subject, kind, key_time):
    """Retrieves a single event.

    Args:
      subject: an entity path or Entity object for the subject of this event
      kind: one of 'durMeasurement', 'durMessage', or 'instMeasurement'
      key_time: the startTime or occurTime in seconds since the epoch
    """
    subject_path = GetEntityPath(subject)
    key = rfc3339.ToTimestamp(key_time).replace(':', '_')
    return ParseEntries(self.Get('%s/%s/%s' % (subject_path, kind, key)))[0]

  def GetEvents(self, subject, kind, min_time, max_time, max_results=1000):
    """Retrieves a list of events within a given time range.

    Args:
      subject: an entity path or Entity object for the subject of this event
      kind: one of 'durMeasurement', 'durMessage', or 'instMeasurement'
      min_time: the minimum startTime or occurTime in seconds since the epoch
      max_time: the maximum startTime or occurTime in seconds since the epoch
      max_results: the maximum number of results to return (but regardless of
          this value, Google servers will not return more than 1000 entries)
    """
    subject_path = GetEntityPath(subject)
    min_timestamp = rfc3339.ToTimestamp(min_time)
    max_timestamp = rfc3339.ToTimestamp(max_time)
    field = kind.startswith('dur') and 'startTime' or 'occurTime'
    return ParseEntries(self.Get('%s/%s?%sMin=%s&%sMax=%s&max-results=%d' % (
        subject_path, kind, field, min_timestamp, field, max_timestamp,
        max_results)))


class BatchAdapter(object):
  """A stand-in for a Service, that queues up events for posting in a batch."""

  def __init__(self, service):
    """Sets up batch posting to a service that provides the Google Meter API.

    Args:
      service: the underlying Service object to which events will be posted
    """
    self.service = service
    self.events = []

  def __repr__(self):
    return '<BatchAdapter for %r>' % self.service

  def PostEvent(self, event):
    """Queue up a single event for later posting."""
    self.events.append(event)

  def Flush(self):
    """Post all the queued events in batches."""
    self.service.BatchPostEvents(self.events)
    self.events = []


class Meter(object):
  """Represents a meter that posts its readings on a particular variable.

  Meter objects have an internal register so they can convert interval or
  register readings to instantaneous or durational events; they also keep
  track of the time between readings to support automatic unit conversion.
  """

  def __init__(self, service, variable, uncertainty, time_uncertainty,
               durational=False, last_read_time=None):
    """Creates a Meter object for a given service and variable.

    Args:
      service: the Google Meter service to post to
      variable: the variable on which to post readings
      uncertainty: the default uncertainty for measurement values posted on
          this meter, as a Quantity (in energy units)
      time_uncertainty: the default uncertainty for measurement times posted
          on this meter, in seconds
      durational: a flag, true if the variable is durational
      last_read_time: the time of the preceding reading (default: None)
    """
    self.service = service
    self.variable = variable
    self.uncertainty = uncertainty
    self.time_uncertainty = time_uncertainty
    self.durational = durational
    self.register = 0.0 * units.KILOWATT_HOUR
    self.last_read_time = last_read_time

  def Reset(self):
    """Puts the meter in a 'no previous reads' state."""
    self.last_read_time = None

  def PostRegisterReading(self, quantity, uncertainty=None, read_time=None):
    """Converts and posts a register reading on this meter's variable.

    Args:
      quantity: the reading as a Quantity (in energy units)
      uncertainty: the uncertainty as a Quantity (in energy units)
      read_time: the time of the reading (default: the current time)
    """

    # Fill in default values for arguments.
    if read_time is None:
      read_time = time.time()
    if uncertainty is None:
      uncertainty = self.uncertainty

    # Compute the new register value.
    new_register = quantity.ConvertTo(units.KILOWATT_HOUR)

    # Depending on self.duration, generate durational or instantaneous events.
    if self.durational:
      if self.last_read_time is not None:
        # The first two register readings are used to produce the first
        # durational event; thereafter each reading produces one event.
        delta = new_register - self.register
        self.PostDur(self.last_read_time, read_time, delta, uncertainty * 2)
    else:
      # Each register reading yields one instantaneous event.
      initial = (self.last_read_time is None)
      self.PostInst(read_time, new_register, uncertainty, initial)

    # Advance the register.
    self.register = new_register
    self.last_read_time = read_time

  def PostIntervalReading(
      self, quantity, uncertainty=None, start_time=None, end_time=None):
    """Converts and posts an interval reading on this meter's variable.

    Args:
      quantity: the reading as a Quantity (in power or energy units)
      uncertainty: the uncertainty as a Quantity (in energy units)
      start_time: the start of the interval (default: the last read or end time)
      end_time: the end of the interval (default: the current time)
    """

    # Fill in default values for arguments.
    if start_time is None:
      start_time = self.last_read_time
    if end_time is None:
      end_time = time.time()
    if uncertainty is None:
      uncertainty = self.uncertainty

    # Compute the new register value.
    if not start_time:
      # When the first interval has no start time, we can't record a reading.
      new_register = self.register
    else:
      if quantity.IsConvertibleTo(units.WATT):  # Convert power to energy.
        quantity *= (end_time - start_time) * units.SECOND
      new_register = self.register + quantity

    # Depending on self.duration, generate durational or instantaneous events.
    if self.durational:
      # Each interval reading yields one durational event.
      self.PostDur(start_time, end_time, quantity, uncertainty)
    else:
      if self.last_read_time is None:
        # The first interval reading yields two instantaneous events, unless
        # the start_time of the interval is unspecified.
        if start_time is None:
          self.PostInst(end_time, self.register, uncertainty, True)
        else:
          self.PostInst(start_time, self.register, uncertainty, True)
          self.PostInst(end_time, new_register, uncertainty, False)
      else:
        # Each subsequent interval reading yields two instantaneous events,
        # unless the start coincides with the end of the last interval.
        if start_time != self.last_read_time:
          self.PostInst(start_time, self.register, uncertainty, True)
        self.PostInst(end_time, new_register, uncertainty, False)

    # Advance the register.
    self.register = new_register
    self.last_read_time = end_time

  def PostDur(self, start_time, end_time, quantity, uncertainty):
    """Posts a single durational measurement to this meter's variable."""
    self.service.PostEvent(DurMeasurement(
        self.variable, start_time, end_time, quantity,
        self.time_uncertainty, self.time_uncertainty, uncertainty))

  def PostInst(self, occur_time, quantity, uncertainty, initial):
    """Posts a single instantaneous measurement to this meter's variable."""
    self.service.PostEvent(InstMeasurement(
        self.variable, occur_time, quantity,
        self.time_uncertainty, uncertainty, initial))
