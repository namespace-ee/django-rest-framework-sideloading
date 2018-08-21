
from rest_framework import serializers


class SideLoadableSerializer(serializers.Serializer):
    pass
    # def __init__(self, *args, **kwargs):
    #     if kwargs.pop('many', False):
    #         raise RuntimeError('Sideloadable serializer can not be initiated with \'many=True\'')
    #     super(SideLoadableSerializer, self).__init__(*args, **kwargs)
    #
    #     print(self.fields)
    #
    #     for name, field in self.fields.items():
    #         if not getattr(field, 'many', False):
    #             raise RuntimeError('SideLoadable field \'%s\' must be set as many=True' % name)
    #         # if not field.read_only:
    #         #     raise RuntimeError('SideLoadable field \'%s\' must be set as read_only=True' % name)
    #         # if not field.allow_null:
    #         #     raise RuntimeError('SideLoadable field \'%s\' must be set as allow_null=True' % name)
    #         # if not field.required:
    #         #     raise RuntimeError('SideLoadable field \'%s\' must be set as required=False' % name)
