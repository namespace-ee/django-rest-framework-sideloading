from rest_framework import serializers


class SideLoadableSerializer(serializers.Serializer):
    def __init__(self, *args, **kwargs):
        super(SideLoadableSerializer, self).__init__(*args, **kwargs)

        # fix for drf browsable api
        # https://github.com/encode/django-rest-framework/blob/master/rest_framework/renderers.py#L530
        self.many = True

        for relation_name in args[0].keys():
            self.fields[relation_name] = kwargs['context']['view'].sideloadable_relations[relation_name](many=True,
                                                                                                         read_only=True)
