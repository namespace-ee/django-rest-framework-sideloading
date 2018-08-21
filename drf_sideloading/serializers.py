from rest_framework import serializers


class SideLoadableSerializer(serializers.Serializer):

    def __init__(self, *args, **kwargs):
        super(SideLoadableSerializer, self).__init__(*args, **kwargs)

        # fix for drf browsable api
        # https://github.com/encode/django-rest-framework/blob/master/rest_framework/renderers.py#L530

        for field in self.fields():
            field.many = True
            field.read_only = True
            field.required = False
            field.allow_null = True

    class Meta:
        fields = '__all__'
