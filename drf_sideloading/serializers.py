from itertools import chain

from rest_framework import serializers

from drf_sideloading.fields import SideloadablePrimaryField, SideloadableRelationField


class SideLoadableSerializer(serializers.Serializer):

    def __init__(self, *args, **kwargs):
        super(SideLoadableSerializer, self).__init__(*args, **kwargs)
        # fix for drf browsable api
        # https://github.com/encode/django-rest-framework/blob/master/rest_framework/renderers.py#L530
        self.many = True

    class Meta:
        fields = '__all__'

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

    def initiate_serializer(self, data, **kwargs):
        """
        get and prepare all required prefetches

        :return:
        :rtype:
        """
        class SerializerXXX(serializers.Serializer):
            for fieldname, field in self.fields:
                fieldname = field.serializer(source=field.source)

        return SerializerXXX
