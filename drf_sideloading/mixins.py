from __future__ import unicode_literals

from rest_framework.response import Response
from itertools import chain

from rest_framework.serializers import ListSerializer

from drf_sideloading.serializers import SideLoadableSerializer


class SideloadableRelationsMixin:
    query_param_name = 'sideload'
    sideloading_serializer_class = None
    _primary_field_name = None
    _sideloadable_fields = None
    relations_to_sideload = None

    def __init__(self, **kwargs):
        self.check_sideloading_serializer_class()
        self._primary_field_name = self.get_primary_field_name()
        self._sideloadable_fields = self.get_sideloadable_fields()
        super(SideloadableRelationsMixin, self).__init__(**kwargs)

    def check_sideloading_serializer_class(self):
        assert self.sideloading_serializer_class is not None, (
            "'%s' should either include a `sideloading_serializer_class` attribute, "
            "or override the `get_sideloading_serializer_class()` method."
            % self.__class__.__name__
        )
        assert issubclass(self.sideloading_serializer_class, SideLoadableSerializer), (
            "'%s' `sideloading_serializer_class` must be a SideLoadableSerializer subclass"
            % self.__class__.__name__
        )

    def get_primary_field_name(self):
        return self.sideloading_serializer_class.Meta.primary

    def get_sideloadable_fields(self):
        sideloadable_fields = self.sideloading_serializer_class._declared_fields
        sideloadable_fields.pop(self._primary_field_name, None)
        return sideloadable_fields

    def list(self, request, *args, **kwargs):
        sideload_params = self.parse_query_param(sideload_parameter=request.query_params.get(self.query_param_name, ''))
        if not sideload_params:
            # do nothing if there is no or empty parameter provided
            return super(SideloadableRelationsMixin, self).list(request, *args, **kwargs)

        # After this `relations_to_sideload` is safe to use
        queryset = self.get_queryset()

        # add prefetches if applicable
        prefetch_relations = self.get_relevant_prefetches()
        if prefetch_relations:
            queryset = queryset.prefetch_related(*prefetch_relations)
        queryset = self.filter_queryset(queryset)

        # create page
        page = self.paginate_queryset(queryset)
        if page is not None:
            sideloadable_page = self.get_sideloadable_page(page)
            serializer = self.sideloading_serializer_class(instance=sideloadable_page)
            return self.get_paginated_response(serializer.data)
        else:
            sideloadable_page = self.get_sideloadable_page_from_queryset(queryset)
            serializer = self.sideloading_serializer_class(instance=sideloadable_page)
            return Response(serializer.data)

    def parse_query_param(self, sideload_parameter):
        """ Parse query param and take validated names

        :param sideload_parameter string
        :return valid relation names list

        comma separated relation names may contain invalid or unusable characters.
        This function finds string match between requested names and defined relation in view

        """
        self.relations_to_sideload = set(sideload_parameter.split(',')) & set(self._sideloadable_fields.keys())
        return self.relations_to_sideload

    def get_relevant_prefetches(self):
        prefetches = getattr(self.sideloading_serializer_class.Meta, 'prefetches', {})
        return set(chain(prefetches.get(relation, []) for relation in self.relations_to_sideload))

    def get_sideloadable_page_from_queryset(self, queryset):
        # this works wonders, but can't be used when page is paginated...
        sideloadable_page = {self._primary_field_name: queryset}
        for relation in self.relations_to_sideload:
            source = self._sideloadable_fields[relation].source or relation
            if isinstance(self._sideloadable_fields[relation], ListSerializer):
                rel_model = self._sideloadable_fields[relation].child.Meta.model
            else:
                rel_model = self._sideloadable_fields[relation].Meta.model
            rel_qs = rel_model.objects.filter(pk__in=queryset.values_list(source, flat=True))
            sideloadable_page[source] = rel_qs
        return sideloadable_page

    def get_sideloadable_page(self, page):
        sideloadable_page = {self._primary_field_name: page}
        for relation in self.relations_to_sideload:
            source = self._sideloadable_fields[relation].source or relation
            sideloadable_page[source] = self.filter_related_objects(related_objects=page, lookup=source)
        return sideloadable_page

    def filter_related_objects(self, related_objects, lookup):
        current_lookup, remaining_lookup = lookup.split('__', 1) if '__' in lookup else (lookup, None)
        related_objects_set = {getattr(r, current_lookup) for r in related_objects}
        if related_objects_set and next(iter(related_objects_set)).__class__.__name__ in ['ManyRelatedManager', 'RelatedManager']:
            related_objects_set = set(chain(*[related_queryset.all() for related_queryset in related_objects_set]))
        if remaining_lookup:
            return self.filter_related_objects(related_objects_set, remaining_lookup)
        return set(related_objects_set) - {'', None}
