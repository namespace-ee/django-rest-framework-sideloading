from collections import OrderedDict

from rest_framework import serializers
from rest_framework.fields import SkipField, empty
from rest_framework.relations import PKOnlyObject


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
            check_for_none = (
                attribute.pk if isinstance(attribute, PKOnlyObject) else attribute
            )
            if check_for_none is None:
                ret[field.field_name] = None
            else:
                ret[field.field_name] = field.to_representation(attribute)

        return ret
