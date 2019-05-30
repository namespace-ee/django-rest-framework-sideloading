import re
from collections import OrderedDict

from rest_framework import serializers
from rest_framework.fields import SkipField, empty
from rest_framework.relations import PKOnlyObject
from rest_framework.serializers import ListSerializer, ModelSerializer


class SideLoadableSerializer(serializers.Serializer):
    def __init__(self, instance=None, data=empty, fields_to_load=None, **kwargs):
        self.fields_to_load = fields_to_load
        super(SideLoadableSerializer, self).__init__(instance=instance, data=data, **kwargs)

    def to_representation(self, instance):
        """
        Object instance -> Dict of primitive datatypes.
        """
        ret = OrderedDict()
        fields = [
            f
            for f in self.fields.values()
            if not f.write_only
            and f.source in instance.keys()
            and f.field_name in self.fields_to_load
        ]

        for field in fields:
            try:
                attribute = field.get_attribute(instance)
            except SkipField:
                continue

            # We skip `to_representation` for `None` values so that fields do
            # not have to explicitly deal with that case.
            #
            # For related fields with `use_pk_only_optimization` we need to
            # resolve the pk value.
            check_for_none = (
                attribute.pk if isinstance(attribute, PKOnlyObject) else attribute
            )
            if check_for_none is None:
                ret[field.field_name] = None
            else:
                ret[field.field_name] = field.to_representation(attribute)

        return ret


class SelectableDataSerializer(serializers.Serializer):

    def __init__(self, *args, **kwargs):
        allowed_fields = kwargs.pop("allowed_fields", [])
        required_fields = kwargs.pop("required_fields", [])

        super(SelectableDataSerializer, self).__init__(*args, **kwargs)
        if allowed_fields or required_fields:
            self.remove_fields(self, set(allowed_fields + required_fields))

    def remove_fields(self, serializer, allowed_fields):
        for field_name in list(serializer.fields.keys()):
            if field_name not in allowed_fields:
                child_fields = [
                    re.compile('^{}__'.format(field_name)).sub('', x)
                    for x in allowed_fields if x.startswith("{}__".format(field_name))
                ]
                if child_fields:
                    child_serializer = serializer.fields[field_name]
                    if isinstance(child_serializer, ListSerializer):
                        child_serializer = child_serializer.child
                    if isinstance(child_serializer, ModelSerializer):
                        self.remove_fields(child_serializer, child_fields)
                        continue

                # pop the field
                serializer.fields.pop(field_name)
