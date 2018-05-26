from itertools import chain

from rest_framework import serializers

from drf_sideloading.fields import SideloadablePrimaryField, SideloadableRelationField


class SideLoadableSerializer(serializers.Serializer):

    def __init__(self, *args, **kwargs):
        super(SideLoadableSerializer, self).__init__(*args, **kwargs)

        # fix for drf browsable api
        # https://github.com/encode/django-rest-framework/blob/master/rest_framework/renderers.py#L530
        self.many = True
        # add many=True, read_only=True to fields as default.
        for relation_name in args[0].keys():
            relation_property = kwargs['context']['view'].sideloadable_relations[relation_name]
            serializer_class = relation_property['serializer']
            self.fields[relation_name] = serializer_class(many=True, read_only=True)

    def get_primary_field_name(self):
        """Determine name of the base(primary) relation"""
        try:
            return next(field_name for field_name, field in self.fields if isinstance(field, SideloadablePrimaryField))
        except StopIteration:
            raise Exception("It is required to define primary model {'primary': True, ...}")
        except AttributeError:
            raise Exception("All sideloadable relations must be defined as dictionaries")

    def get_sideloadable_fields(self):
        return {field_name: field for field_name, field in self.fields if isinstance(field, SideloadableRelationField)}

    def get_primary_serializer(self):
        return self.fields[self.get_primary_field_name()].serializer

    def get_prefetches(self):
        """
        get and prepare all required prefetches

        :return:
        :rtype:
        """
        return set(chain(field.get_prefetches() for field in self.get_sideloadable_fields().values()))
