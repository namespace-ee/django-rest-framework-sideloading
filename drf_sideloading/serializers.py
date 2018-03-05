from rest_framework import serializers


class SideLoadableSerializer(serializers.Serializer):
    def __init__(self, *args, **kwargs):
        super(SideLoadableSerializer, self).__init__(*args, **kwargs)

        # fix for drf browsable api
        # https://github.com/encode/django-rest-framework/blob/master/rest_framework/renderers.py#L530
        self.many = True

        for relation_name in args[0].keys():
            relation_property = kwargs['context']['view'].sideloadable_relations[relation_name]
            serializer_class = relation_property['serializer']
            self.fields[relation_name] = serializer_class(many=True, read_only=True)
