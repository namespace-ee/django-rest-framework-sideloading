from rest_framework.pagination import CursorPagination, _positive_int
from rest_framework.response import Response


class LinkHeaderCursorPagination(CursorPagination):
    page_size_query_param = "page_size"
    max_page_size = 1000
    ordering = "id"

    def get_page_size(self, request):
        page_size_query_param = self.page_size_query_param

        if page_size_query_param:
            try:
                return _positive_int(
                    request.query_params[page_size_query_param], strict=True, cutoff=self.max_page_size
                )
            except (KeyError, ValueError):
                pass

        return self.page_size

    def get_paginated_response(self, data):
        headers = dict()

        link_rel_and_hrefs = [("next", self.get_next_link()), ("prev", self.get_previous_link())]
        links = ['<{link}>; rel="{rel}"'.format(rel=rel, link=link) for rel, link in link_rel_and_hrefs if link]

        if links:
            headers["Link"] = ", ".join(links)

        return Response(data, headers=headers)

    def _get_position_from_instance(self, instance, ordering):
        # hack to allow related field lookups to be in ordering filters
        field_name = ordering[0].lstrip("-")
        if isinstance(instance, dict):
            attr = instance[field_name]
        else:
            attr = instance
            for x in field_name.split("__"):
                attr = getattr(attr, x)
        return str(attr)
