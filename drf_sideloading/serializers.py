
from rest_framework import serializers

class SideLoadableSerializer(serializers.Serializer):
    # TODO
    # 1. check there are sideloadable_relations defined
    # 2. write tests
    def __init__(self, *args, **kwargs):
        super(SideLoadableSerializer, self).__init__(*args, **kwargs)

        for relation_name in args[0].keys():
            self.fields[relation_name] = kwargs['context']['view'].sideloadable_relations[relation_name](many=True, read_only=True)
