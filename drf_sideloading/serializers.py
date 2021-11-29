from collections import OrderedDict

from rest_framework import serializers
from rest_framework.fields import SkipField, empty


class SideLoadableSerializer(serializers.Serializer):
    fields_to_load = None
    relations_to_sideload = None

    def __init__(self, instance=None, data=empty, relations_to_sideload=None, **kwargs):
        self.relations_to_sideload = relations_to_sideload
        self.fields_to_load = [self.Meta.primary] + list(relations_to_sideload.keys())
        super(SideLoadableSerializer, self).__init__(instance=instance, data=data, **kwargs)

    def to_representation(self, instance):
        """
        Object instance -> Dict of primitive datatypes.
        """
        ret = OrderedDict()
        fields = [
            f
            for f in self.fields.values()
            if not f.write_only and f.source in instance.keys() and f.field_name in self.fields_to_load
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
            if getattr(attribute, "pk", attribute) is None:
                ret[field.field_name] = None
            else:
                ret[field.field_name] = field.to_representation(attribute)

        return ret
