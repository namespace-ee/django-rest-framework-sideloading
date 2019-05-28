from __future__ import unicode_literals

from collections import defaultdict

import six
import copy

from itertools import chain

from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.response import Response
from rest_framework.serializers import ListSerializer

from drf_sideloading.renderers import BrowsableAPIRendererWithoutForms
from drf_sideloading.serializers import SideLoadableSerializer


class SideloadableRelationsMixin(object):
    query_param_name = "sideload"
    flat_param_name = "flat"
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

    def initialize_request(self, request, *args, **kwargs):
        request = super(SideloadableRelationsMixin, self).initialize_request(
            request=request, *args, **kwargs
        )

        sideload_params = self.parse_query_param(
            sideload_parameter=request.query_params.get(self.query_param_name, "")
        )
        if request.method == "GET" and sideload_params:
            # When sideloading disable BrowsableAPIForms
            if BrowsableAPIRenderer in self.renderer_classes:
                renderer_classes = (
                    list(self.renderer_classes)
                    if isinstance(self.renderer_classes, tuple)
                    else self.renderer_classes
                )
                renderer_classes = [
                    BrowsableAPIRendererWithoutForms if r == BrowsableAPIRenderer else r
                    for r in renderer_classes
                ]
                self.renderer_classes = renderer_classes

        return request

    def list(self, request, *args, **kwargs):
        sideload_params = self.parse_query_param(
            sideload_parameter=request.query_params.get(self.query_param_name, "")
        )

        # Do not sideload unless params and GET method
        if request.method != "GET" or not sideload_params:
            return super(SideloadableRelationsMixin, self).list(
                request, *args, **kwargs
            )
        # check if result needs to be flattened
        flatten = request.query_params.get(self.flat_param_name) in ['true', '1']

        # After this `relations_to_sideload` is safe to use
        queryset = self.get_queryset()

        # Add prefetches if applicable
        prefetch_relations = self.get_relevant_prefetches()
        if prefetch_relations:
            queryset = queryset.prefetch_related(*prefetch_relations)
        queryset = self.filter_queryset(queryset)

        # Create page
        page = self.paginate_queryset(queryset)
        if page is not None:
            sideloadable_page = self.get_sideloadable_page(page)
            serializer = self.sideloading_serializer_class(
                instance=sideloadable_page,
                fields_to_load=[self._primary_field_name]
                + list(self.relations_to_sideload),
                context={"request": request},
            )
            if flatten:
                return self.get_paginated_response(self.flatten_sideloaded_data(serialized_data=serializer.data))
            return self.get_paginated_response(serializer.data)
        else:
            sideloadable_page = self.get_sideloadable_page_from_queryset(queryset)
            serializer = self.sideloading_serializer_class(
                instance=sideloadable_page,
                fields_to_load=[self._primary_field_name]
                + list(self.relations_to_sideload),
                context={"request": request},
            )
            if flatten:
                return Response(self.flatten_sideloaded_data(serialized_data=serializer.data))
            return Response(serializer.data)

    def flatten_data(self, input_data, initial_key):
        out = {}

        def flatten(data, key):
            if isinstance(data, dict):
                for dict_key, dict_value in data.items():
                    flatten(data=dict_value, key="{}__{}".format(key, dict_key))
            elif isinstance(data, list):
                if any(isinstance(list_obj, (dict, list)) for list_obj in data):
                    for i, list_obj in enumerate(data):
                        flatten(data=list_obj, key="{}__{}".format(key, i))
                else:
                    out[key] = data
            else:
                out[key] = data

        flatten(input_data, initial_key)
        return out

    def flatten_sideloaded_data(self, serialized_data):
        primary_objects = serialized_data.pop(self._primary_field_name)
        sideloaded_data = defaultdict(dict)
        relation_sources = {}
        for relation in self.relations_to_sideload:
            relation_sources[relation] = self.sideloading_serializer_class._declared_fields.get(relation).source
            for data in serialized_data[relation]:
                sideloaded_data[relation][data["url"]] = self.flatten_data(data, relation_sources[relation])

        for object in primary_objects:
            for relation in self.relations_to_sideload:
                object.update(sideloaded_data[relation][object.pop(relation_sources[relation])])
        return primary_objects

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
        related_objects_set = {getattr(r, current_lookup) for r in related_objects} - {None}
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
