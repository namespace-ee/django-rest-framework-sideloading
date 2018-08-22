from collections import OrderedDict

from rest_framework import serializers
from rest_framework.fields import SkipField
from rest_framework.relations import PKOnlyObject


class SideLoadableSerializer(serializers.Serializer):
    def __init__(self, *args, **kwargs):
        if kwargs.pop('many', False):
            raise RuntimeError('Sideloadable serializer can not be initiated with \'many=True\'')
        super(SideLoadableSerializer, self).__init__(*args, **kwargs)

        if not self.Meta.primary:
            raise RuntimeError('Sideloadable serializer must have a Meta attribute called primary!')

        for name, field in self.fields.items():
            if not getattr(field, 'many', False):
                raise RuntimeError('SideLoadable field \'%s\' must be set as many=True' % name)

    def to_representation(self, instance):
        """
        Object instance -> Dict of primitive datatypes.
        """
        ret = OrderedDict()
        fields = [f for f in self._readable_fields if f.source in instance.keys()]

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
            check_for_none = attribute.pk if isinstance(attribute, PKOnlyObject) else attribute
            if check_for_none is None:
                ret[field.field_name] = None
            else:
                ret[field.field_name] = field.to_representation(attribute)

        return ret
