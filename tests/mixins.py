# -*- coding: utf-8
from __future__ import unicode_literals


class OtherMixin(object):
    """ Mixin for testing purposes
        Check if `self.action` attribute is availavle
    """

    def get_serializer_class(self):
        if not hasattr(self, "action"):
            raise AttributeError("Action is not available")
        return super(OtherMixin, self).get_serializer_class()
