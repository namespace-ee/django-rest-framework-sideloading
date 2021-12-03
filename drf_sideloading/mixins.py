import copy
import itertools
import re
from itertools import chain
from typing import List, Dict

from django.db.models import Prefetch
from rest_framework.generics import get_object_or_404
from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.response import Response
from rest_framework.serializers import ListSerializer, ModelSerializer

from drf_sideloading.renderers import BrowsableAPIRendererWithoutForms
from drf_sideloading.serializers import SideLoadableSerializer


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

    def clean_prefetches(self, relation, value, ensure_list=False):
        if not value:
            cleaned_value = None
        elif isinstance(value, str):
            cleaned_value = value
        elif isinstance(value, list):
            cleaned_value = [self.clean_prefetches(relation=relation, value=val) for val in value]
            # filter out empty values
            cleaned_value = [val for val in cleaned_value if val]
        elif isinstance(value, dict):
            if "lookup" not in value:
                raise ValueError(f"Sideloadable field '{relation}' Prefetch 'lookup' must be set!")
            # if "queryset" not in prefetches:
            #     raise ValueError(f"Sideloadable field '{relation}' Prefetch 'queryset' must be set!")
            cleaned_value = Prefetch(**value, to_attr=relation)
        elif isinstance(value, Prefetch):
            # check that to_attr is set the same as the field!
            if not value.to_attr:
                if value.prefetch_to != relation:
                    raise ValueError(f"Sideloadable field '{relation}' Prefetch 'to_attr' must be set!")
            elif value.to_attr != relation:
                raise ValueError(f"Sideloadable field '{relation}' Prefetch 'to_attr' must match the field name!")
            cleaned_value = value
        else:
            raise ValueError("Sideloadable prefetch values must be a list of strings or Prefetch objects")

        if ensure_list:
            if not cleaned_value:
                return []
            elif not isinstance(cleaned_value, list):
                return [cleaned_value]

        return cleaned_value

    def get_sideloading_prefetches(self) -> Dict:
        cleaned_prefetches = {}
        user_defined_prefetches = getattr(self.sideloading_serializer_class.Meta, "prefetches", {})

        # set source as the default prefetch object
        for relation, field in self._sideloadable_fields.items():
            user_prefetches = user_defined_prefetches.get(relation)
            if relation in user_defined_prefetches and user_prefetches in [None, []]:
                # user has explicitly defined no prefetching
                cleaned_prefetches[relation] = []
            elif not user_prefetches:
                # default to field source if not defined by user
                cleaned_prefetches[relation] = [field.child.source]
            elif isinstance(user_prefetches, dict):
                # This is a multi source field!
                # make prefetches for all relations separately
                cleaned_prefetches[relation] = {}
                for rel, rel_prefetches in user_prefetches.items():
                    prefetches = self.clean_prefetches(relation=rel, value=rel_prefetches, ensure_list=True)
                    cleaned_prefetches[relation][rel] = prefetches
            else:
                cleaned_prefetches[relation] = self.clean_prefetches(
                    relation=relation, value=user_prefetches, ensure_list=True
                )

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

    def get_relevant_prefetches(self) -> List:
        if not self._prefetches:
            return []
        # Prefetch object must be defined before string type prefetches to avoid ValueError:
        #       "'supplier' lookup was already seen with a different queryset. "
        #       "You may need to adjust the ordering of your lookups."

        # maybe we even need to define the string type as a separate Prefetch object
        # in case the second one overwrites the first one?!

        prefetches = []
        for relation, selections in self.relations_to_sideload.items():
            relation_prefetches = self._prefetches[relation]
            if not relation_prefetches:
                continue
            elif isinstance(relation_prefetches, list):
                prefetches.extend(relation_prefetches)
            elif isinstance(relation_prefetches, dict):
                # multi source field, check for source selection
                if not selections or set(selections) == set(relation_prefetches.keys()) - {"__all__"}:
                    # add __all__ prefetch
                    prefetch_all = relation_prefetches["__all__"]
                    if prefetch_all:
                        prefetches.extend(prefetch_all)
                else:
                    # combine prefetches:
                    prefetch_combined = [x for sel in selections for x in relation_prefetches.get(sel) or [] if x]

                    if prefetch_combined:
                        prefetches.extend(prefetch_combined)
            else:
                raise ValueError("Got invalid prefech type!")

        # prefetches = set(pf for relation in self.relations_to_sideload for pf in self._prefetches[relation] or [])
        # prefetches = list(pf if isinstance(pf, Prefetch) else Prefetch(pf) for pf in prefetches)
        return list(prefetches)

    def get_sideloadable_page_from_queryset(self, queryset):
        # this works wonders, but can't be used when page is paginated...
        sideloadable_page = {self._primary_field_name: queryset}
        for relation, source_keys in self.relations_to_sideload.items():
            field = self._sideloadable_fields[relation]
            field_source = field.child.source or relation

            if not isinstance(self._sideloadable_fields[relation], ListSerializer):
                raise RuntimeError("SideLoadable field '{}' must be set as many=True".format(relation))

            if not getattr(field.child, "source", None):
                if relation not in sideloadable_page:
                    sideloadable_page[relation] = set()

                # TODO: case when no or all keys are present, use the __all__ prefetch if present,
                #  else loop through all the relations.
                # TODO: the correct field might be relation even if source is present
                #  Check this usage.

                for source_key in source_keys or [field_source]:
                    sideloadable_page[relation] |= self.filter_related_objects(
                        related_objects=queryset, lookup=source_key
                    )
                continue

            # find all related object ids
            sideloadable_page[relation] = self.filter_related_objects(related_objects=queryset, lookup=field_source)

        return sideloadable_page

    def get_sideloadable_page(self, page):
        sideloadable_page = {self._primary_field_name: page}
        for relation, source_keys in self.relations_to_sideload.items():
            field = self._sideloadable_fields[relation]
            field_source = field.child.source or relation

            # fixme:  field.source can't be used in case prefetces with "to_attr" other than source is used

            if not isinstance(field, ListSerializer):
                raise RuntimeError("SideLoadable field '{}' must be set as many=True".format(relation))

            if relation not in sideloadable_page:
                sideloadable_page[relation] = set()

            # TODO: case when no or all keys are present, use the __all__ prefetch if present,
            #  else loop through all the relations.
            # TODO: the correct field might be relation even if source is present
            #  Check this usage.

            for source_key in source_keys or [field_source]:
                sideloadable_page[relation] |= self.filter_related_objects(related_objects=page, lookup=source_key)

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
