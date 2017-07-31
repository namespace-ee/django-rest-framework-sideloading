from rest_framework.response import Response

from .serializers import SideLoadableSerializer


class SideloadableRelationsMixin(object):
    query_param_name = 'sideload'
    default_primary_object_name = 'self'

    relation_names = []

    def __init__(self, **kwargs):
        self.primary_serializer_class = self.get_serializer_class()

        if not self.sideloadable_relations:
            raise Exception
        self.primary_object_name = self.get_primary_relation_name()

    def get_primary_relation_name(self):
        for relation_name, properties in self.sideloadable_relations.iteritems():
            if isinstance(properties, dict):
                for name, value in properties.iteritems():
                    if name == 'primary' and value:
                        if not properties.get('serializer'):
                            self.sideloadable_relations[relation_name]['serializer'] = self.primary_serializer_class
                        return relation_name
        self.sideloadable_relations[self.default_primary_object_name] = self.primary_serializer_class
        return self.default_primary_object_name

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

    def get_sideloadable_page(self, page):
        sideloadable_page = {self.primary_object_name: page}
        for rel in self.relation_names:
            single_relation_set = set()
            for row in page:
                if hasattr(row, rel):
                    if getattr(row, rel).__class__.__name__ == 'ManyRelatedManager':
                        single_relation_set = single_relation_set | set(getattr(row, rel).all())
                    else:
                        single_relation_set.add(getattr(row, rel))
            sideloadable_page[rel] = single_relation_set
        return sideloadable_page

    def get_serializer_class(self):
        if self.relation_names and self.action == 'list':
            return SideLoadableSerializer

        return super(SideloadableRelationsMixin, self).get_serializer_class()
