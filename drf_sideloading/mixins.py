from rest_framework.response import Response

from .serializers import SideLoadableSerializer


class SideloadableRelationsMixin(object):
    query_param_name = 'sideload'

    relation_names = []
    base_model_name = ''
    relations_set = {}

    def list(self, request, *args, **kwargs):
        sideload = request.query_params.get(self.get_param_name(), None)
        if not sideload:
            # do nothing if there is no or empty parameter provided
            return super(SideloadableRelationsMixin, self).list(request, *args, **kwargs)

        self.parse_query_param(sideload)

        if not self.relation_names:
            # do nothing if there is intersection between provided parameters and defined `sideloadable_relations`
            return super(SideloadableRelationsMixin, self).list(request, *args, **kwargs)

        # After this `relation_names` is safe to use
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            sideloadable_page = self.get_sideloadable_page(page)

            serializer = self.get_serializer(sideloadable_page)
            return self.get_paginated_response(serializer.data)

        sideloadable_page = self.get_sideloadable_page(queryset)

        serializer = self.get_serializer(sideloadable_page)
        return Response(serializer.data)

    def get_param_name(self):
        return self.query_param_name

    def parse_query_param(self, sideload_relations):
        relation_names = sideload_relations.split(',')
        # only take valid names
        self.relation_names = set(relation_names) & set(self.sideloadable_relations.keys())
        return relation_names

    def get_sideloadable_page(self, page):
        sideloadable_page = {self.base_model_name: page}
        for rel in self.relation_names:
            single_relation_set = set()
            for row in page:
                single_relation_set.add(getattr(row, rel))
            sideloadable_page[rel] = single_relation_set
        return sideloadable_page

    def get_serializer_class(self):
        if self.relation_names and self.action == 'list':
            return SideLoadableSerializer

        return super(SideloadableRelationsMixin, self).get_serializer_class()
