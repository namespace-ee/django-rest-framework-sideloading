class OtherMixin(object):
    """Mixin for testing purposes

        Only access to `self.action` to make sure that it is available
    """

    def get_serializer_class(self):
        if self.action in [u'user_permissions']:
            pass
        return super(OtherMixin, self).get_serializer_class()
