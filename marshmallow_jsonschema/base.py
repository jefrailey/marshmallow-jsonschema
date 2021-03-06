import datetime
import uuid
import decimal

from marshmallow import fields, missing, Schema
from marshmallow.compat import text_type, binary_type, basestring
from marshmallow.class_registry import get_class

__all__ = ['JSONSchema']


TYPE_MAP = {
    dict: {
        'type': 'object',
    },
    list: {
        'type': 'array',
    },
    datetime.time: {
        'type': 'string',
        'format': 'time',
    },
    datetime.timedelta: {
        # TODO explore using 'range'?
        'type': 'string',
    },
    datetime.datetime: {
        'type': 'string',
        'format': 'date-time',
    },
    datetime.date: {
        'type': 'string',
        'format': 'date',
    },
    uuid.UUID: {
        'type': 'string',
        'format': 'uuid',
    },
    text_type: {
        'type': 'string',
    },
    binary_type: {
        'type': 'string',
    },
    decimal.Decimal: {
        'type': 'number',
        'format': 'decimal',
    },
    set: {
        'type': 'array',
    },
    tuple: {
        'type': 'array',
    },
    float: {
        'type': 'number',
        'format': 'float',
    },
    int: {
        'type': 'number',
        'format': 'integer',
    },
    bool: {
        'type': 'boolean',
    },
}


class JSONSchema(Schema):
    properties = fields.Method('get_properties')
    type = fields.Constant('object')
    required = fields.Method('get_required')

    def get_properties(self, obj):
        mapping = {v: k for k, v in obj.TYPE_MAPPING.items()}
        mapping[fields.Email] = text_type
        mapping[fields.Dict] = dict
        mapping[fields.List] = list
        mapping[fields.Url] = text_type
        mapping[fields.LocalDateTime] = datetime.datetime
        properties = {}
        for field_name, field in sorted(obj.fields.items()):
            if hasattr(field, '_jsonschema_type_mapping'):
                schema = field._jsonschema_type_mapping()
            elif field.__class__ in mapping:
                pytype = mapping[field.__class__]
                schema = _from_python_type(field, pytype)
            elif isinstance(field, fields.Nested):
                schema = _from_nested_schema(field)
            else:
                raise ValueError('unsupported field type %s' % field)
            properties[field.name] = schema
        return properties

    def get_required(self, obj):
        required = []
        for field_name, field in sorted(obj.fields.items()):
            if field.required:
                required.append(field.name)
        return required


def _from_python_type(field, pytype):
    json_schema = {
        'title': field.attribute or field.name,
    }
    for key, val in TYPE_MAP[pytype].items():
        json_schema[key] = val
    if field.default is not missing:
        json_schema['default'] = field.default

    return json_schema


def _from_nested_schema(field):
    only = field.only
    exclude = field.exclude
    # `marshmallow.fields.Nested` keyword argument `only` expects
    # a string, iterable, or `None`, but `marshmallow.Schema` keyword
    # argument `only` accepts an iterable. Convert from string to
    # a tuple.
    if isinstance(only, basestring):
        only = (only,)
    # `field.nested` can be declared as a subclass of
    # `marshmallow.Schema` or an instance of `basestring`. If the latter,
    # then the subclass should be available via
    # `marshmallow.class_registry`
    try:
        nested_schema = field.nested(only=only, exclude=exclude)
    except TypeError:  # field.nested is a basestring
        nested_schema = get_class(field.nested)(only=only, exclude=exclude)
    schema = JSONSchema().dump(nested_schema).data
    if field.many:
        schema = {
            'type': ["array"] if field.required else ['array', 'null'],
            'items': schema
        }
    return schema
