from __future__ import unicode_literals

from rest_framework.response import Response
from itertools import chain

from drf_sideloading.fields import SideloadablePrimaryField
from .serializers import SideLoadableSerializer


class SideloadableRelationsMixin(object):
    query_param_name = 'sideload'
    sideloadable_serializer_class = None
    _sideloadable_serializer = None
    _sideloadable_fields = None
    _primary_field_name = None

    def __init__(self):
        # check and initiate required fields
        self._sideloadable_serializer = self.get_sideloadable_serializer_class()
        self._primary_field_name = self._sideloadable_serializer.get_primary_field_name()
        self._sideloadable_fields = self._sideloadable_serializer.get_sideloadable_fields()

    def get_sideloadable_serializer_class(self):
        assert self.sideloadable_serializer_class is not None, (
            "'%s' should either include a `sideloadable_serializer_class` attribute, "
            "or override the `get_sideloadable_serializer_class()` method."
            % self.__class__.__name__
        )
        assert isinstance(self.sideloadable_serializer_class, SideLoadableSerializer), (
            "'%s' `sideloadable_serializer_class` must be a SideLoadableSerializer instance"
            % self.__class__.__name__
        )
        return self.sideloadable_serializer_class

    def list(self, request, *args, **kwargs):
        sideload_params = request.query_params.get(self.query_param_name, None)
        if not sideload_params:
            # do nothing if there is no or empty parameter provided
            return super(SideloadableRelationsMixin, self).list(request, *args, **kwargs)

        self.parse_query_param(sideload_params)
        if not self.relations_to_sideload:
            # do nothing if there is no intersection between provided parameters and defined `sideloadable_relations`
            return super(SideloadableRelationsMixin, self).list(request, *args, **kwargs)

        # After this `relations_to_sideload` is safe to use
        queryset = self.get_queryset()

        # add prefetches if applicable
        prefetch_relations = self._sideloadable_serializer.get_prefetches()
        if prefetch_relations:
            queryset = queryset.prefetch_related(*prefetch_relations)
        queryset = self.filter_queryset(queryset)

        # create page
        page = self.paginate_queryset(queryset)
        if page is not None:
            sideloadable_page = self.get_sideloadable_page(page)
            serializer = self.get_sideloadable_serializer(sideloadable_page)
            return self.get_paginated_response(serializer.data)

        sideloadable_page = self.get_sideloadable_page_from_queryset(queryset)
        serializer = self.get_sideloadable_serializer(sideloadable_page)
        return Response(serializer.data)

    def parse_query_param(self, sideload_parameter):
        """ Parse query param and take validated names

        :param sideload_parameter string
        :return valid relation names list

        comma separated relation names may contain invalid or unusable characters.
        This function finds string match between requested names and defined relation in view

        """
        self.relations_to_sideload = set(sideload_parameter.split(',')) & set(self._sideloadable_serializer.get_sideloadable_fields().keys())
        return self.relations_to_sideload

    def get_sideloadable_page_from_queryset(self, queryset):
        # this works wonders, but can't be used when page is paginated...
        sideloadable_page = {self._primary_field_name: queryset}
        for rel in self.relations_to_sideload:
            # single_relation_set = set()
            source = self.sideloadable_relations[rel].get('source', rel)
            # i don't like how the model is found. there has to be a better way for this.. but it works
            rel_model = self.sideloadable_relations[rel]['serializer'].Meta.model
            rel_qs = rel_model.objects.filter(pk__in=queryset.values_list(source, flat=True))

            sideloadable_page[rel] = rel_qs
        return sideloadable_page

    def filter_related_objects(self, related_objects, lookup):
        current_lookup, remaining_lookup = lookup.split('__', 1) if '__' in lookup else (lookup, None)
        related_objects_set = {getattr(r, current_lookup) for r in related_objects}
        if related_objects_set and next(iter(related_objects_set)).__class__.__name__ in ['ManyRelatedManager', 'RelatedManager']:
            related_objects_set = set(chain(*[related_queryset.all() for related_queryset in related_objects_set]))
        if remaining_lookup:
            return self.filter_related_objects(related_objects_set, remaining_lookup)
        return set(related_objects_set) - {'', None}

    def get_sideloadable_page(self, page):
        sideloadable_page = {self._primary_field_name: page}
        for rel in self.relations_to_sideload:
            source = self._sideloadable_fields[rel].source or rel
            sideloadable_page[rel] = self.filter_related_objects(related_objects=page, lookup=source)
        return sideloadable_page

    def get_sideloadable_serializer(self, *args, **kwargs):
        """
        Return the serializer instance that should be used for validating and
        deserializing input, and for serializing output.
        """
        serializer_class = self._sideloadable_serializer
        kwargs['context'] = self.get_serializer_context()
        return serializer_class(*args, **kwargs)
