import copy
import itertools
import re
from itertools import chain

from django.db.models import Prefetch
from rest_framework.generics import get_object_or_404
from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.response import Response
from rest_framework.serializers import ListSerializer, ModelSerializer

from drf_sideloading.renderers import BrowsableAPIRendererWithoutForms
from drf_sideloading.serializers import SideLoadableSerializer


class MultiSourceSerializerMixin:
    sources = []

    def __init__(self, sources, source=None, read_only=None, *args, **kwargs):
        self.sources = sources
        if not sources:
            raise ValueError("'sources' is a required argument")
        if not source:
            source = sources[0]  # used only for ModelSerializer binding
        if read_only is False:
            raise ValueError("'read_only' can't be set to False")

        super().__init__(source=source, read_only=True, *args, *kwargs)


class SideloadableRelationsMixin(object):
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
        ), "'{}' should either include a `sideloading_serializer_class` attribute, ".format(self.__class__.__name__)
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
            self.sideloading_serializer_class.Meta.primary in self.sideloading_serializer_class._declared_fields
        ), "Sideloadable serializer Meta.primary must point to a field in the serializer!"
        if getattr(self.sideloading_serializer_class.Meta, "prefetches", None) is not None:
            assert isinstance(
                self.sideloading_serializer_class.Meta.prefetches, dict
            ), "Sideloadable serializer Meta attribute 'prefetches' must be a dict."

        # check serializer fields:
        for name, field in self.sideloading_serializer_class._declared_fields.items():
            assert getattr(field, "many", None), "SideLoadable field '{}' must be set as many=True".format(name)
            assert isinstance(
                field.child, ModelSerializer
            ), "SideLoadable field '{}' serializer must be inherited from ModelSerializer".format(name)

    def get_primary_field_name(self):
        return self.sideloading_serializer_class.Meta.primary

    def get_sideloadable_fields(self):
        sideloadable_fields = copy.deepcopy(self.sideloading_serializer_class._declared_fields)
        sideloadable_fields.pop(self._primary_field_name)
        return sideloadable_fields

    def get_sideloading_prefetches(self):
        cleaned_prefetches = {}
        user_defined_prefetches = getattr(self.sideloading_serializer_class.Meta, "prefetches", {})

        # set source as the default prefetch object
        for relation, field in self._sideloadable_fields.items():
            if isinstance(field.child, MultiSourceSerializerMixin):
                cleaned_prefetches[relation] = field.child.sources
            else:
                cleaned_prefetches[relation] = [field.child.source or relation]

            # FIXME:
            # create Prefetch object if a queryset is defined?
            # if field.source.queryset

        for relation, prefetches in user_defined_prefetches.items():
            # remove prefetching if requested by the user
            if prefetches is None:
                cleaned_prefetches[relation] = []
                continue

            # cast to list
            if not isinstance(prefetches, list):
                prefetches = [prefetches]

            # check the prefetches are correct
            for prefetch in prefetches:
                if isinstance(prefetch, str):
                    pass
                elif isinstance(prefetch, Prefetch):
                    # check that to_attr is set the same as the field!
                    if not prefetch.to_attr:
                        if prefetch.prefetch_to != relation:
                            raise ValueError(f"Sideloadable field '{relation}' Prefetch 'to_attr' must be set!")
                    elif prefetch.to_attr != relation:
                        raise ValueError(
                            f"Sideloadable field '{relation}' Prefetch 'to_attr' must match the field name!"
                        )
                else:
                    raise ValueError("Sideloadable prefetch values must be a list of strings or Prefetch objects")
            cleaned_prefetches[relation] = prefetches

        return cleaned_prefetches

    def initialize_request(self, request, *args, **kwargs):
        request = super(SideloadableRelationsMixin, self).initialize_request(request=request, *args, **kwargs)

        self.parse_query_param(sideload_parameter=request.query_params.get(self.query_param_name, ""))
        if request.method == "GET" and self.relations_to_sideload:
            # When sideloading disable BrowsableAPIForms
            if BrowsableAPIRenderer in self.renderer_classes:
                renderer_classes = (
                    list(self.renderer_classes) if isinstance(self.renderer_classes, tuple) else self.renderer_classes
                )
                renderer_classes = [
                    BrowsableAPIRendererWithoutForms if r == BrowsableAPIRenderer else r for r in renderer_classes
                ]
                self.renderer_classes = renderer_classes

        return request

    def list(self, request, *args, **kwargs):
        self.parse_query_param(sideload_parameter=request.query_params.get(self.query_param_name, ""))

        # Do not sideload unless params and GET method
        if request.method != "GET" or not self.relations_to_sideload:
            return super(SideloadableRelationsMixin, self).list(request, *args, **kwargs)

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
                relations_to_sideload=self.relations_to_sideload,
                context={"request": request},
            )
            return self.get_paginated_response(serializer.data)
        else:
            sideloadable_page = self.get_sideloadable_page_from_queryset(queryset)
            serializer = self.sideloading_serializer_class(
                instance=sideloadable_page,
                relations_to_sideload=self.relations_to_sideload,
                context={"request": request},
            )
            return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        self.parse_query_param(sideload_parameter=request.query_params.get(self.query_param_name, ""))

        # Do not sideload unless params and GET method
        if request.method != "GET" or not self.relations_to_sideload:
            return super(SideloadableRelationsMixin, self).retrieve(request, *args, **kwargs)

        # return object with sideloading serializer
        queryset = self.get_sideloadable_object_as_queryset()
        sideloadable_page = self.get_sideloadable_page_from_queryset(queryset)
        serializer = self.sideloading_serializer_class(
            instance=sideloadable_page,
            relations_to_sideload=self.relations_to_sideload,
            context={"request": request},
        )
        return Response(serializer.data)

    def parse_query_param(self, sideload_parameter):
        """
        Parse query param and take validated names

        :param sideload_parameter string
        :return valid relation names list

        comma separated relation names may contain invalid or unusable characters.
        This function finds string match between requested names and defined relation in view

        new:

        response changed to dict as the sources for multi source fields must be selectable.

        """
        sideloadable_relations = set(self._sideloadable_fields.keys())

        self.relations_to_sideload = {}
        for param in re.split(",\s*(?![^\[\]]*\])", sideload_parameter):
            try:
                fieldname, sources_str = param.split("[", 1)
                self.relations_to_sideload[fieldname] = set(sources_str.strip("]").split(","))
            except ValueError:
                if param in sideloadable_relations:
                    self.relations_to_sideload[param] = None
        return self.relations_to_sideload

    def get_relevant_prefetches(self):
        if not self._prefetches:
            return set()
        # Prefetch object must be defined before string type prefetches to avoid ValueError:
        #       "'supplier' lookup was already seen with a different queryset. "
        #       "You may need to adjust the ordering of your lookups."

        # maybe we even need to define the string type as a separate Prefetch object
        # in case the second one overwrites the first one?!

        # or set Prefetch_object first to always raise the error?
        # TODO: combine and filter prefetches for multi source fields
        prefetches = set(pf for relation in self.relations_to_sideload for pf in self._prefetches[relation] or [])
        prefetches = list(pf if isinstance(pf, Prefetch) else Prefetch(pf) for pf in prefetches)
        return prefetches

    def get_sideloadable_page_from_queryset(self, queryset):
        # this works wonders, but can't be used when page is paginated...
        sideloadable_page = {self._primary_field_name: queryset}
        for relation, source_keys in self.relations_to_sideload.items():
            field = self._sideloadable_fields[relation]
            field_source = field.source or relation
            rel_model = field.child.Meta.model

            if not isinstance(self._sideloadable_fields[relation], ListSerializer):
                raise RuntimeError("SideLoadable field '{}' must be set as many=True".format(relation))

            if isinstance(field.child, MultiSourceSerializerMixin):
                # find correct sources if MultiSourceField has filtering applied
                sources = [getattr(self._sideloadable_fields[source], "source", source) for source in source_keys or []]
                # find all related object ids
                relation_ids = set(itertools.chain(*queryset.values_list(*(sources or field.child.sources))))
            else:
                # find all related object ids
                relation_ids = queryset.values_list(field_source, flat=True)

            sideloadable_page[field_source] = rel_model.objects.filter(pk__in=relation_ids)

        return sideloadable_page

    def get_sideloadable_page(self, page):
        sideloadable_page = {self._primary_field_name: page}
        for relation, sources in self.relations_to_sideload.items():
            field = self._sideloadable_fields[relation]
            field_source = field.source or relation
            if not isinstance(field, ListSerializer):
                raise RuntimeError("SideLoadable field '{}' must be set as many=True".format(relation))

            if isinstance(field.child, MultiSourceSerializerMixin):
                sideloadable_page[relation] = set()
                if field_source not in sideloadable_page:
                    sideloadable_page[field_source] = set()
                for source in sources or field.child.sources:
                    sideloadable_page[field_source] |= self.filter_related_objects(related_objects=page, lookup=source)
            else:
                source = self._sideloadable_fields[relation].source or relation
                sideloadable_page[source] = self.filter_related_objects(related_objects=page, lookup=source)

        return sideloadable_page

    def get_sideloadable_object_as_queryset(self):
        """
        mimics DRF original method get_object()
        Returns the object the view is displaying with sideloaded models prefetched.

        You may want to override this if you need to provide non-standard
        queryset lookups.  Eg if objects are referenced using multiple
        keyword arguments in the url conf.
        """
        # Add prefetches if applicable
        queryset = self.get_queryset()
        prefetch_relations = self.get_relevant_prefetches()
        if prefetch_relations:
            queryset = queryset.prefetch_related(*prefetch_relations)
        queryset = self.filter_queryset(queryset)

        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        assert lookup_url_kwarg in self.kwargs, (
            "Expected view %s to be called with a URL keyword argument "
            'named "%s". Fix your URL conf, or set the `.lookup_field` '
            "attribute on the view correctly." % (self.__class__.__name__, lookup_url_kwarg)
        )

        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        queryset = queryset.filter(**filter_kwargs)

        # check single object fetched
        obj = get_object_or_404(queryset)
        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return queryset

    def filter_related_objects(self, related_objects, lookup):
        current_lookup, remaining_lookup = lookup.split("__", 1) if "__" in lookup else (lookup, None)
        lookup_values = [getattr(r, current_lookup) for r in related_objects if getattr(r, current_lookup) is not None]

        if lookup_values:
            if lookup_values[0].__class__.__name__ in ["ManyRelatedManager", "RelatedManager"]:
                related_objects_set = set(chain(*[related_queryset.all() for related_queryset in lookup_values]))
            elif isinstance(lookup_values[0], list):
                related_objects_set = set(chain(*[related_list for related_list in lookup_values]))
            else:
                related_objects_set = set(lookup_values)
        else:
            related_objects_set = set()

        if remaining_lookup:
            return self.filter_related_objects(related_objects_set, remaining_lookup)
        return set(related_objects_set) - {"", None}
