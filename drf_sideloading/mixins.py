from __future__ import unicode_literals

from rest_framework.response import Response
from itertools import chain

from .serializers import SideLoadableSerializer


class SideloadableRelationsMixin(object):
    query_param_name = 'sideload'
    relation_names = []

    def __init__(self, **kwargs):
        if not hasattr(self, 'sideloadable_relations'):
            raise Exception("define `sideloadable_relations` class variable, while using `SideloadableRelationsMixin`")
        self.primary_object_name = self.get_primary_relation_name()

    def get_primary_relation_name(self):
        """Determine name of the base(primary) relation"""
        try:
            return next(k for k, v in self.sideloadable_relations.items() if v.get('primary') is True)
        except StopIteration:
            raise Exception("It is required to define primary model {'primary': True, ...}")
        except AttributeError:
            raise Exception("All sideloadable relations must be defined as dictionaries")

    def list(self, request, *args, **kwargs):
        sideload = request.query_params.get(self.query_param_name, None)
        if not sideload:
            # do nothing if there is no or empty parameter provided
            return super(SideloadableRelationsMixin, self).list(request, *args, **kwargs)

        self.parse_query_param(sideload)
        if not self.relation_names:
            # do nothing if there is no intersection between provided parameters and defined `sideloadable_relations`
            return super(SideloadableRelationsMixin, self).list(request, *args, **kwargs)

        # After this `relation_names` is safe to use
        queryset = self.get_queryset()

        prefetch_relations = [
            relation['prefetch'] if isinstance(relation['prefetch'], list) else [relation['prefetch']]
            for name, relation in self.sideloadable_relations.items()
            if name in self.relation_names and relation.get('prefetch')
        ]
        if prefetch_relations:
            queryset = queryset.prefetch_related(*set(chain(*prefetch_relations)))
        queryset = self.filter_queryset(queryset)

        page = self.paginate_queryset(queryset)
        if page is not None:
            sideloadable_page = self.get_sideloadable_page(page)
            serializer = self.get_serializer(sideloadable_page)
            return self.get_paginated_response(serializer.data)

        sideloadable_page = self.get_sideloadable_page_from_queryset(queryset)
        serializer = self.get_serializer(sideloadable_page)
        return Response(serializer.data)

    def parse_query_param(self, sideload_relations):
        """ Parse query param and take validated names

        :param sideload_relations string
        :return valid relation names list

        comma separated relation names may contain invalid or unusable characters.
        This function finds string match between requested names and defined relation in view

        """
        relation_names = sideload_relations.split(',')
        self.relation_names = \
            (set(relation_names) & set(self.sideloadable_relations.keys())) - set([self.primary_object_name])
        return relation_names

    def get_sideloadable_page_from_queryset(self, queryset):
        # this works wonders, but can't be used when page is paginated...
        sideloadable_page = {self.primary_object_name: queryset}
        for rel in self.relation_names:
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
        sideloadable_page = {self.primary_object_name: page}
        for rel in self.relation_names:
            source = self.sideloadable_relations[rel].get('source', rel)
            sideloadable_page[rel] = self.filter_related_objects(related_objects=page, lookup=source)
        return sideloadable_page

    def get_serializer_class(self):
        if self.relation_names and self.action == 'list':
            return SideLoadableSerializer

        return super(SideloadableRelationsMixin, self).get_serializer_class()
