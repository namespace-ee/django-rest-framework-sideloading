from __future__ import unicode_literals

import six
import copy

from rest_framework.response import Response
from itertools import chain

from rest_framework.serializers import ListSerializer

from drf_sideloading.serializers import SideLoadableSerializer


class SideloadableRelationsMixin(object):
    """
    TODO: Implement some protection for too large queries.
        * limit the number of sideloadable elements?
            if over limit:
            - raise error
            - show warning
            - paginate, show first page and add a link to remaining paginated list of related elements?
            - show only the link to paginated list of related elements?

    """

    query_param_name = "sideload"
    sideloading_serializer_class = None
    _primary_field_name = None
    _sideloadable_fields = None
    relations_to_sideload = None

    def __init__(self, **kwargs):
        self.check_sideloading_serializer_class()
        self._primary_field_name = self.get_primary_field_name()
        self._sideloadable_fields = self.get_sideloadable_fields()
        self._prefetches = self.get_sideloading_prefetches()
        super(SideloadableRelationsMixin, self).__init__(**kwargs)

    def check_sideloading_serializer_class(self):
        assert (
            self.sideloading_serializer_class is not None
        ), "'{}' should either include a `sideloading_serializer_class` attribute, ".format(
            self.__class__.__name__
        )
        assert issubclass(
            self.sideloading_serializer_class, SideLoadableSerializer
        ), "'{}' `sideloading_serializer_class` must be a SideLoadableSerializer subclass".format(
            self.__class__.__name__
        )
        assert not getattr(
            self.sideloading_serializer_class, "many", None
        ), "Sideloadable serializer can not be 'many=True'!"

        # Check Meta class
        assert hasattr(
            self.sideloading_serializer_class, "Meta"
        ), "Sideloadable serializer must have a Meta class defined with the 'primary' field name!"
        assert getattr(
            self.sideloading_serializer_class.Meta, "primary", None
        ), "Sideloadable serializer must have a Meta attribute called primary!"
        assert (
            self.sideloading_serializer_class.Meta.primary
            in self.sideloading_serializer_class._declared_fields
        ), "Sideloadable serializer Meta.primary must point to a field in the serializer!"
        if (
            getattr(self.sideloading_serializer_class.Meta, "prefetches", None)
            is not None
        ):
            assert isinstance(
                self.sideloading_serializer_class.Meta.prefetches, dict
            ), "Sideloadable serializer Meta attribute 'prefetches' must be a dict."

        # check serializer fields:
        for name, field in self.sideloading_serializer_class._declared_fields.items():
            assert getattr(
                field, "many", None
            ), "SideLoadable field '{}' must be set as many=True".format(name)

        # check serializer fields:
        for name, field in self.sideloading_serializer_class._declared_fields.items():
            assert getattr(
                field, "many", None
            ), "SideLoadable field '{}' must be set as many=True".format(name)

    def get_primary_field_name(self):
        return self.sideloading_serializer_class.Meta.primary

    def get_sideloadable_fields(self):
        sideloadable_fields = copy.deepcopy(
            self.sideloading_serializer_class._declared_fields
        )
        sideloadable_fields.pop(self._primary_field_name, None)
        return sideloadable_fields

    def get_sideloading_prefetches(self):
        prefetches = getattr(self.sideloading_serializer_class.Meta, "prefetches", {})
        if not prefetches:
            return None
        cleaned_prefetches = {}
        for k, v in prefetches.items():
            if v is not None:
                if isinstance(v, list):
                    cleaned_prefetches[k] = v
                elif isinstance(v, six.string_types):
                    cleaned_prefetches[k] = [v]
                else:
                    raise RuntimeError(
                        "Sideloadable prefetch values must be presented either as a list or a string"
                    )
        return cleaned_prefetches

    def list(self, request, *args, **kwargs):
        sideload_params = self.parse_query_param(
            sideload_parameter=request.query_params.get(self.query_param_name, "")
        )
        if not sideload_params:
            # do nothing if there is no or empty parameter provided
            return super(SideloadableRelationsMixin, self).list(
                request, *args, **kwargs
            )

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
            serializer = self.sideloading_serializer_class(
                instance=sideloadable_page, context={"request": request}
            )
            return self.get_paginated_response(serializer.data)
        else:
            sideloadable_page = self.get_sideloadable_page_from_queryset(queryset)
            serializer = self.sideloading_serializer_class(
                instance=sideloadable_page, context={"request": request}
            )
            return Response(serializer.data)

    def parse_query_param(self, sideload_parameter):
        """
        Parse query param and take validated names

        :param sideload_parameter string
        :return valid relation names list

        comma separated relation names may contain invalid or unusable characters.
        This function finds string match between requested names and defined relation in view

        """
        self.relations_to_sideload = set(sideload_parameter.split(",")) & set(
            self._sideloadable_fields.keys()
        )
        return self.relations_to_sideload

    def get_relevant_prefetches(self):
        if not self._prefetches:
            return set()
        return set(
            pf
            for relation in self.relations_to_sideload
            for pf in self._prefetches.get(relation, [])
        )

    def get_sideloadable_page_from_queryset(self, queryset):
        # this works wonders, but can't be used when page is paginated...
        sideloadable_page = {self._primary_field_name: queryset}
        for relation in self.relations_to_sideload:
            if not isinstance(self._sideloadable_fields[relation], ListSerializer):
                raise RuntimeError(
                    "SideLoadable field '{}' must be set as many=True".format(relation)
                )

            source = self._sideloadable_fields[relation].source or relation
            rel_model = self._sideloadable_fields[relation].child.Meta.model
            rel_qs = rel_model.objects.filter(
                pk__in=queryset.values_list(source, flat=True)
            )
            sideloadable_page[source] = rel_qs
        return sideloadable_page

    def get_sideloadable_page(self, page):
        sideloadable_page = {self._primary_field_name: page}
        for relation in self.relations_to_sideload:
            if not isinstance(self._sideloadable_fields[relation], ListSerializer):
                raise RuntimeError(
                    "SideLoadable field '{}' must be set as many=True".format(relation)
                )

            source = self._sideloadable_fields[relation].source or relation
            sideloadable_page[source] = self.filter_related_objects(
                related_objects=page, lookup=source
            )
        return sideloadable_page

    def filter_related_objects(self, related_objects, lookup):
        current_lookup, remaining_lookup = (
            lookup.split("__", 1) if "__" in lookup else (lookup, None)
        )
        related_objects_set = {getattr(r, current_lookup) for r in related_objects}
        if related_objects_set and next(
            iter(related_objects_set)
        ).__class__.__name__ in ["ManyRelatedManager", "RelatedManager"]:
            related_objects_set = set(
                chain(
                    *[
                        related_queryset.all()
                        for related_queryset in related_objects_set
                    ]
                )
            )
        if remaining_lookup:
            return self.filter_related_objects(related_objects_set, remaining_lookup)
        return set(related_objects_set) - {"", None}
