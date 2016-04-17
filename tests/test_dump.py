from marshmallow import Schema, fields
from marshmallow_jsonschema import JSONSchema
from jsonschema import Draft4Validator

from . import BaseTest, UserSchema, Group


class TestDumpSchema(BaseTest):

    def _validate_schema(self, schema):
        '''
        raises jsonschema.exceptions.SchemaError
        '''
        Draft4Validator.check_schema(schema)

    def test_dump_schema(self):
        schema = UserSchema()
        json_schema = JSONSchema()
        dumped = json_schema.dump(schema).data
        self._validate_schema(dumped)
        self.assertGreater(len(schema.fields), 1)
        for field_name, field in schema.fields.items():
            self.assertIn(field_name, dumped['properties'])

    def test_default(self):
        schema = UserSchema()
        json_schema = JSONSchema()
        dumped = json_schema.dump(schema).data
        self._validate_schema(dumped)
        self.assertEqual(dumped['properties']['id']['default'], 'no-id')

    def test_unknown_typed_field_throws_valueerror(self):

        class Invalid(fields.Field):
            def _serialize(self, value, attr, obj):
                return value

        class UserSchema(Schema):
            favourite_colour = Invalid()

        schema = UserSchema()
        json_schema = JSONSchema()
        with self.assertRaises(ValueError):
            dumped = json_schema.dump(schema).data

    def test_unknown_typed_field(self):

        class Colour(fields.Field):

            def _jsonschema_type_mapping(self):
                return {
                    'type': 'string',
                }

            def _serialize(self, value, attr, obj):
                r, g, b = value
                r = hex(r)[2:]
                g = hex(g)[2:]
                b = hex(b)[2:]
                return '#' + r + g + b

        class UserSchema(Schema):
            name = fields.String(required=True)
            favourite_colour = Colour()

        schema = UserSchema()
        json_schema = JSONSchema()
        dumped = json_schema.dump(schema).data
        self.assertEqual(dumped['properties']['favourite_colour'],
                        {'type': 'string'})

    def test_nested_only_exclude(self):

        schema = Group()
        json_schema = JSONSchema()
        dumped = json_schema.dump(schema).data
        for key, field in schema.declared_fields.items():
            original_fields = field.schema.declared_fields.keys()
            nested_dict = dumped['properties'][key]['items']['properties']
            actual_properties = list(nested_dict.keys())
            if field.only:  # only takes precedence over exclude
                if isinstance(field.only, str):
                    expected_properties = [field.only]
                else:
                    expected_properties = list(field.only)
            elif field.exclude:
                expected_properties = list(original_fields -
                                           set(field.exclude))
            else:
                expected_properties = original_fields
            self.assertEqual(sorted(expected_properties),
                             sorted(actual_properties))
