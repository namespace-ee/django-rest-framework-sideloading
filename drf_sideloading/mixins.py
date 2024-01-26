import copy
import re
from itertools import chain
from typing import Dict, Optional, Union, Tuple, Set

from django.db.models import Prefetch
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import RetrieveModelMixin, ListModelMixin
from rest_framework.response import Response
from rest_framework.serializers import ListSerializer

from drf_sideloading.serializers import SideLoadableSerializer


class SideloadableRelationsMixin(object):
    sideloading_query_param_name = "sideload"
    sideloading_serializer_class = None

    def __init__(self, **kwargs):
        super(SideloadableRelationsMixin, self).__init__(**kwargs)

    # fixme: This is an awkward method
    def get_sideloading_variables_from_serializer(self, request):
        sideloading_serializer_class = self.get_sideloading_serializer_class()
        self.check_sideloading_serializer_class(serializer_class=sideloading_serializer_class)
        # primary field
        primary_field_name = sideloading_serializer_class.Meta.primary
        # sideloadable fields
        sideloadable_fields = copy.deepcopy(sideloading_serializer_class._declared_fields)
        sideloadable_fields.pop(primary_field_name)
        # cleaned prefetches
        prefetches = self._gather_all_prefetches(
            sideloadable_fields=sideloadable_fields,
            user_defined_prefetches=getattr(sideloading_serializer_class.Meta, "prefetches", None),
        )
        relations_to_sideload = self.parse_query_param(
            sideload_parameter=request.query_params.get(self.sideloading_query_param_name, ""),
        )
        self.check_sideload_params(
            relations_to_sideload=relations_to_sideload, sideloadable_fields=sideloadable_fields, prefetches=prefetches
        )

        # find applicable prefetches
        if relations_to_sideload:
            prefetch_relations, relations_sources = self._get_relevant_prefetches(
                sideloadable_fields=sideloadable_fields,
                relations_to_sideload=relations_to_sideload,
                cleaned_prefetches=prefetches,
            )
        else:
            prefetch_relations = None
            relations_sources = None
        return (
            sideloading_serializer_class,
            primary_field_name,
            sideloadable_fields,
            prefetches,
            relations_to_sideload,
            prefetch_relations,
            relations_sources,
        )

    def parse_query_param(self, sideload_parameter: str) -> Dict:
        """
        Parse query param and take validated names

        :param sideload_parameter string
        :return valid relation names list

        comma separated relation names may contain invalid or unusable characters.
        This function finds string match between requested names and defined relation in view

        new:

        response changed to dict as the sources for multi source fields must be selectable.

        """
        if not sideload_parameter:
            return {}

        relations_to_sideload = {}
        for param in re.split(r",\s*(?![^\[\]]*\])", sideload_parameter):
            if not param:
                continue
            try:
                fieldname, sources_str = param.split("[", 1)
                relations = set(sources_str.strip("]").split(","))
                if any(relations):
                    relations_to_sideload[fieldname] = set(sources_str.strip("]").split(","))
            except ValueError:
                relations_to_sideload[param] = None

        return relations_to_sideload

    def check_sideload_params(self, relations_to_sideload: Dict, sideloadable_fields: Dict, prefetches: Dict):
        for relation, source_keys in relations_to_sideload.items():
            if relation not in sideloadable_fields:
                msg = _(f"'{relation}' is not one of the available choices.")
                raise ValidationError({self.sideloading_query_param_name: [msg]})
            if source_keys is not None:
                if not isinstance(source_keys, (set, list)):
                    raise ValueError(f"Source_keys must be a list or set not '{type(source_keys)}'")
                if not isinstance(prefetches.get(relation), dict):
                    msg = _(f"'{relation}' does not have multiple sources")
                    raise ValidationError({self.sideloading_query_param_name: [msg]})
                for source_key in source_keys:
                    if source_key not in prefetches[relation].keys():
                        msg = _(f"'{source_key}' is not one of the available source keys for relation '{relation}'")
                        raise ValidationError({self.sideloading_query_param_name: [msg]})

    def check_sideloading_serializer_class(self, serializer_class):
        if not serializer_class:
            raise ValueError(f"'{self.__class__.__name__}' sideloading_serializer_class not found")
        if not issubclass(serializer_class, SideLoadableSerializer):
            raise ValueError(
                f"'{self.__class__.__name__}' sideloading_serializer_class must be a SideLoadableSerializer subclass"
            )
        serializer_class.check_setup()

    def get_sideloading_serializer(self, *args, **kwargs):
        """
        Return the sideloading_serializer instance that should be used for serializing output.
        """
        sideloading_serializer_class = self.get_sideloading_serializer_class()
        kwargs["context"] = self.get_sideloading_serializer_context()
        return sideloading_serializer_class(*args, **kwargs)

    def get_sideloading_serializer_class(self):
        """
        Return the class to use for the sideloading_serializer.
        Defaults to using `self.sideloading_serializer_class`.

        You may want to override this if you need to provide different
        serializations depending on the incoming request.

        (Eg. admins get full serialization, others get basic serialization)
        """
        assert self.sideloading_serializer_class is not None, (
            f"'{self.__class__.__name__}' should either include a `sideloading_serializer_class` attribute, "
            f"or override the `get_sideloading_serializer_class()` method."
        )

        return self.sideloading_serializer_class

    def get_sideloading_serializer_context(self):
        """
        Extra context provided to the serializer class.
        """
        return {"request": self.request, "format": self.format_kwarg, "view": self}

    # modified DRF methods

    def retrieve(self, request, *args, **kwargs):
        if not isinstance(self, RetrieveModelMixin):
            # The viewset does not have RetrieveModelMixin and therefore the method is not allowed
            return self.http_method_not_allowed(request, *args, **kwargs)

        if self.sideloading_query_param_name not in request.query_params:
            try:
                return super().retrieve(request=request, *args, **kwargs)
            except AttributeError:
                # self.retrieve() method was not declared before this mixin.
                # Make sure the SideloadableRelationsMixin is defined higher than RetrieveModelMixin.
                return self.http_method_not_allowed(request, *args, **kwargs)

        (
            sideloading_serializer_class,
            primary_field_name,
            sideloadable_fields,
            prefetches,
            relations_to_sideload,
            prefetch_relations,
            relations_sources,
        ) = self.get_sideloading_variables_from_serializer(request=request)

        if not relations_to_sideload:
            try:
                return super().retrieve(request=request, *args, **kwargs)
            except AttributeError:
                # self.retrieve() method was not declared before this mixin.
                # Make sure the SideloadableRelationsMixin is defined higher than RetrieveModelMixin.
                return self.http_method_not_allowed(request, *args, **kwargs)

        # return object with sideloading serializer
        queryset, relations_sources = self.get_sideloadable_object_as_queryset(
            relations_to_sideload=relations_to_sideload,
            sideloadable_fields=sideloadable_fields,
            cleaned_prefetches=prefetches,
        )
        sideloadable_page = self.get_sideloadable_page_from_queryset(
            queryset=queryset,
            primary_field_name=primary_field_name,
            sideloadable_fields=sideloadable_fields,
            relations_to_sideload=relations_to_sideload,
            relations_sources=relations_sources,
        )
        serializer = self.get_sideloading_serializer(
            instance=sideloadable_page,
            relations_to_sideload=relations_to_sideload,
            context={"request": request},
        )
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        if not isinstance(self, ListModelMixin):
            # The viewset does not have ListModelMixin and therefore the method is not allowed
            return self.http_method_not_allowed(request, *args, **kwargs)

        if request.method != "GET" or self.sideloading_query_param_name not in request.query_params:
            try:
                return super().list(request=request, *args, **kwargs)
            except AttributeError:
                # self.list() method was not declared before this mixin.
                # Make sure the SideloadableRelationsMixin is defined higher than ListModelMixin.
                return self.http_method_not_allowed(request, *args, **kwargs)

        (
            sideloading_serializer_class,
            primary_field_name,
            sideloadable_fields,
            prefetches,
            relations_to_sideload,
            prefetch_relations,
            relations_sources,
        ) = self.get_sideloading_variables_from_serializer(request=request)

        if not relations_to_sideload:
            try:
                return super().list(request=request, *args, **kwargs)
            except AttributeError:
                # self.list() method was not declared before this mixin.
                # Make sure the SideloadableRelationsMixin is defined higher than ListModelMixin.
                return self.http_method_not_allowed(request, *args, **kwargs)

        # After this `relations_to_sideload` is safe to use
        queryset = self.get_queryset()
        if prefetch_relations:
            queryset = queryset.prefetch_related(*[v for k, v in sorted(prefetch_relations.items())])
        queryset = self.filter_queryset(queryset)

        # Create page
        page = self.paginate_queryset(queryset)
        if page is not None:
            sideloadable_page = self.get_sideloadable_page(
                page=page,
                primary_field_name=primary_field_name,
                sideloadable_fields=sideloadable_fields,
                relations_to_sideload=relations_to_sideload,
                relations_sources=relations_sources,
            )
            serializer = self.get_sideloading_serializer(
                instance=sideloadable_page,
                relations_to_sideload=relations_to_sideload,
                context={"request": request},
            )
            return self.get_paginated_response(serializer.data)
        else:
            sideloadable_page = self.get_sideloadable_page_from_queryset(
                queryset=queryset,
                primary_field_name=primary_field_name,
                sideloadable_fields=sideloadable_fields,
                relations_to_sideload=relations_to_sideload,
                relations_sources=relations_sources,
            )
            serializer = self.get_sideloading_serializer(
                instance=sideloadable_page,
                relations_to_sideload=relations_to_sideload,
                context={"request": request},
            )
            return Response(serializer.data)

    def get_sideloadable_page_from_queryset(
        self,
        queryset,
        primary_field_name: str,
        sideloadable_fields: Dict,
        relations_to_sideload: Dict,
        relations_sources: Dict,
    ):
        """
        Populates page with sideloaded data by collecting ids form sideloaded values and then making into a query
        """

        if not relations_to_sideload:
            raise ValueError("relations_to_sideload is required")
        # this works wonders, but can't be used when page is paginated...
        sideloadable_page = {primary_field_name: queryset}

        for relation, source_keys in relations_to_sideload.items():
            field = sideloadable_fields[relation]
            field_source = field.child.source
            source_model = field.child.Meta.model
            relation_key = field_source or relation

            related_ids = set()
            if isinstance(relations_sources.get(relation), dict):
                for src_key, src in relations_sources[relation].items():
                    if not (source_keys is None or src_key in source_keys or src_key == "__all__"):
                        raise ValueError(f"Unexpected relation source '{src_key}' used")
                    related_ids |= set(queryset.values_list(src, flat=True))
            else:
                related_ids |= set(queryset.values_list(field_source or relations_sources[relation], flat=True))

            sideloadable_page[relation_key] = source_model.objects.filter(id__in=related_ids)

        return sideloadable_page

    def get_sideloadable_page(
        self,
        page,
        primary_field_name: str,
        sideloadable_fields: Dict,
        relations_to_sideload: Dict,
        relations_sources: Dict,
    ):
        """
        Populates page with sideloaded data by collecting distinct values form sideloaded data
        """
        sideloadable_page = {primary_field_name: page}
        for relation, source_keys in relations_to_sideload.items():
            field = sideloadable_fields[relation]
            field_source = field.child.source
            relation_key = field_source or relation

            if not isinstance(field, ListSerializer):
                raise RuntimeError("SideLoadable field '{}' must be set as many=True".format(relation))

            if relation not in sideloadable_page:
                sideloadable_page[relation_key] = set()

            if isinstance(relations_sources.get(relation), dict):
                # Multi source relation
                for src_key, src in relations_sources[relation].items():
                    if not (source_keys is None or src_key in source_keys or src_key == "__all__"):
                        raise ValueError(f"Unexpected relation source '{src_key}' used")
                    sideloadable_page[relation_key] |= self.filter_related_objects(related_objects=page, lookup=src)
            else:
                sideloadable_page[relation_key] |= self.filter_related_objects(
                    related_objects=page, lookup=field_source or relations_sources[relation]
                )

        return sideloadable_page

    def get_sideloadable_object_as_queryset(self, relations_to_sideload, sideloadable_fields, cleaned_prefetches):
        """
        mimics DRF original method get_object()
        Returns the object the view is displaying with sideloaded models prefetched.

        You may want to override this if you need to provide non-standard
        queryset lookups.  Eg if objects are referenced using multiple
        keyword arguments in the url conf.
        """
        # Add prefetches if applicable
        queryset = self.get_queryset()
        prefetch_relations, relations_sources = self._get_relevant_prefetches(
            sideloadable_fields=sideloadable_fields,
            relations_to_sideload=relations_to_sideload,
            cleaned_prefetches=cleaned_prefetches,
        )

        if prefetch_relations:
            queryset = queryset.prefetch_related(*[v for k, v in sorted(prefetch_relations.items())])
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

        return queryset, relations_sources

    def filter_related_objects(self, related_objects, lookup: Optional[str]) -> Set:
        current_lookup, remaining_lookup = lookup.split("__", 1) if "__" in lookup else (lookup, None)
        lookup_values = [
            getattr(r, current_lookup) for r in related_objects if getattr(r, current_lookup, None) is not None
        ]

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
            return self.filter_related_objects(related_objects=related_objects_set, lookup=remaining_lookup)
        return set(related_objects_set) - {"", None}

    # internal_methods:

    def _clean_prefetches(self, field, relation, value, ensure_list=False):
        if not value:
            raise ValueError(f"Sideloadable field '{relation}' prefetch or source must be set!")
        elif isinstance(value, str):
            cleaned_value = value
        elif isinstance(value, list):
            cleaned_value = [self._clean_prefetches(field=field, relation=relation, value=val) for val in value]
            # filter out empty values
            cleaned_value = [val for val in cleaned_value if val]
        elif isinstance(value, dict):
            if "lookup" not in value:
                raise ValueError(f"Sideloadable field '{relation}' Prefetch 'lookup' must be set!")
            if value.get("to_attr") and field.child.source and field.child.source != value.get("to_attr"):
                raise ValueError(
                    f"Sideloadable field '{relation}' Prefetch 'to_attr' can't be used with source defined. "
                    f"Remove source from field serializer."
                )
            if value.get("queryset") or value.get("to_attr"):
                if not value.get("to_attr"):
                    value["to_attr"] = relation
                cleaned_value = Prefetch(**value)
            else:
                cleaned_value = value["lookup"]
        elif isinstance(value, Prefetch):
            # check that Prefetch.to_attr is set the same as the field.source!
            if value.to_attr and field.child.source and field.child.source != value.to_attr:
                raise ValueError(
                    f"Sideloadable field '{relation}' Prefetch 'to_attr' can't be different from source defined. "
                    f"Tip: Remove source from field serializer."
                )
            cleaned_value = value
        else:
            raise ValueError("Sideloadable prefetch values must be a list of strings or Prefetch objects")

        if ensure_list:
            if not cleaned_value:
                return []
            elif not isinstance(cleaned_value, list):
                return [cleaned_value]

        return cleaned_value

    def _gather_all_prefetches(self, sideloadable_fields: Dict, user_defined_prefetches: Optional[Dict]) -> Dict:
        """
        this method finds all prefetches required and checks if they are correctly defined
        """
        cleaned_prefetches = {}

        if not sideloadable_fields:
            raise ValueError("'sideloadable_fields' is a required argument")

        if not user_defined_prefetches:
            user_defined_prefetches = {}

        # find prefetches for all sideloadable relations
        for relation, field in sideloadable_fields.items():
            user_prefetches = user_defined_prefetches.get(relation)
            field_source = field.child.source
            if relation in user_defined_prefetches and not user_prefetches:
                raise ValueError(f"prefetches for field '{relation}' have been left empty")
            elif not user_prefetches:
                if field_source:
                    # default to field source if not defined by user
                    cleaned_prefetches[relation] = [field_source]
                elif getattr(self.get_serializer_class().Meta.model, relation, None):
                    # default to parent serializer model field with the relation name if it exists
                    cleaned_prefetches[relation] = [relation]
                else:
                    raise ValueError(f"Either source or prefetches must be set for sideloadable field '{relation}'")
            elif isinstance(user_prefetches, (str, list, Prefetch)):
                cleaned_prefetches[relation] = self._clean_prefetches(
                    field=field, relation=relation, value=user_prefetches, ensure_list=True
                )
            elif isinstance(user_prefetches, dict):
                # This is a multi source field!
                # make prefetches for all relations separately
                cleaned_prefetches[relation] = {}
                for rel, rel_prefetches in user_prefetches.items():
                    relation_prefetches = self._clean_prefetches(
                        field=field, relation=rel, value=rel_prefetches, ensure_list=True
                    )
                    cleaned_prefetches[relation][rel] = relation_prefetches
            else:
                raise NotImplementedError(f"prefetch with type '{type(user_prefetches)}' is not implemented")

        return cleaned_prefetches

    def _add_prefetch(self, prefetches: Dict, prefetch: Union[str, Prefetch]) -> str:
        # add prefetch to prefetches dict and return the prefetch_attr
        # TODO: merge multi source prefetches if possible
        # TODO: check Prefetch vs str type prefeches.

        if isinstance(prefetch, str):
            prefetch_attr = prefetch
        elif isinstance(prefetch, Prefetch):
            prefetch_attr = prefetch.to_attr or prefetch.prefetch_through
        else:
            raise NotImplementedError(f"Adding '{type(prefetch)}' type object to prefetches has not been implemented")

        existing_prefetch = prefetches.get(prefetch_attr)

        if not existing_prefetch:
            prefetches[prefetch_attr] = prefetch
        elif isinstance(existing_prefetch, str):
            if prefetch != prefetches[prefetch_attr]:
                raise ValueError("Two different prefetches for the same attribute")
        elif isinstance(existing_prefetch, Prefetch):
            # TODO: check for matching Prefetches not just a pointer match.
            if prefetch.queryset != existing_prefetch.queryset:
                raise ValueError("Prefetch with queryset overwriting existing prefetch")
            # todo: find other clashing prefetch cases

        return prefetch_attr

    def _get_relevant_prefetches(
        self, sideloadable_fields: Dict, relations_to_sideload: Dict, cleaned_prefetches: Dict
    ) -> Tuple[Dict, Dict]:
        """
        Collects all relevant prefetches and returns
        compressed prefetches and sources per relation to be used later.
        """

        relations_sources = {}
        gathered_prefetches = {}

        if not sideloadable_fields:
            raise ValueError("'sideloadable_fields' is a required argument")
        if not relations_to_sideload:
            raise ValueError("'relations_to_sideload' is a required argument")
        if not cleaned_prefetches:
            raise ValueError("'cleaned_prefetches' is a required argument")

        for relation, requested_sources in relations_to_sideload.items():
            relation_prefetches = cleaned_prefetches.get(relation)
            field_source = sideloadable_fields[relation].child.source
            data_source = field_source

            # gather prefetches and sources
            if relation_prefetches is None:
                raise ValueError(
                    f"Missing prefetch for field '{relation}'. Check '_gather_all_prefetches' works correctly"
                )
            elif isinstance(relation_prefetches, list):
                # No multi source used, load from source unless Prefetch object used
                if requested_sources:
                    raise ValueError(f"Got 'requested_sources' for field '{relation}' without MultiSource prefetches")

                # find source
                if data_source:
                    pass
                elif len(relation_prefetches) != 1:
                    if any(pf == relation for pf in relation_prefetches):
                        data_source = relation
                    else:
                        raise ValueError(
                            "Unless source is defined or the field name matches the model, "
                            "there can only be one prefetch, to define the relation"
                        )
                elif isinstance(relation_prefetches[0], str):
                    data_source = relation_prefetches[0]
                elif isinstance(relation_prefetches[0], Prefetch):
                    data_source = relation_prefetches[0].to_attr or relation_prefetches[0].prefetch_through
                else:
                    raise ValueError(
                        "Unless source is defined or the field name matches the model, "
                        "There can only be one prefetch, to define the relation and it must be a string or Prefetch"
                    )

                if any(isinstance(prefetch, Prefetch) for prefetch in relation_prefetches):
                    # load data from Prefetch.to_attr object used
                    if len(relation_prefetches) != 1:
                        raise ValueError(
                            "If Prefetch is used, there can only one prefetch. "
                            "Others must be defined within Prefetch.queryset"
                        )
                    # take values from Prefetch.to_attr
                    prefetch_attr = self._add_prefetch(prefetches=gathered_prefetches, prefetch=relation_prefetches[0])
                    relations_sources[relation] = data_source or prefetch_attr
                else:
                    # all prefetches are strings:

                    # find source
                    if not data_source:
                        if getattr(self.get_serializer_class().Meta.model, relation, None):
                            data_source = relation
                        elif len(relation_prefetches) == 1:
                            data_source = relation_prefetches[0]
                        elif any(pf == relation for pf in relation_prefetches):
                            data_source = relation
                        else:
                            raise ValueError(
                                "Unless source is defined or the field name matches the model, "
                                "there can only be one prefetch, to define the relation"
                            )

                    for prefetch in relation_prefetches:
                        self._add_prefetch(prefetches=gathered_prefetches, prefetch=prefetch)
                    relations_sources[relation] = data_source

            # if not field_source
            elif isinstance(relation_prefetches, dict):
                # its a MultiSource field, fetch values from sources defined with prefetches.
                if field_source:
                    raise ValueError("Multi source field with source defined in serializer.")

                if requested_sources:
                    for invalid_source_key in set(requested_sources) - set(relation_prefetches.keys()):
                        msg = _(
                            f"'{invalid_source_key}' is not one of the available source keys for relation '{relation}'"
                        )
                        raise ValidationError({self.sideloading_query_param_name: [msg]})

                elif "__all__" in relation_prefetches:
                    # find source in case it's not a Prefetch object.
                    # requested_sources = [relation_prefetches["__all__"].to_attr]
                    raise NotImplementedError("default prefetch for all in not implemented")
                elif relation_prefetches:
                    requested_sources = list(relation_prefetches.keys())
                else:
                    raise ValueError("Prefetches missing")

                # collect field prefetches and sources
                relations_sources[relation] = dict()
                for source_key in requested_sources:
                    if relations_sources[relation].get(source_key):
                        raise ValueError(
                            "Multiple sources defined for single multi source field. "
                            "Prefetch or select related within Prefetch queryset."
                        )
                    for source_prefetch in relation_prefetches[source_key]:
                        if not isinstance(source_prefetch, list):
                            source_prefetch = [source_prefetch]
                        if len(source_prefetch) > 1:
                            raise NotImplementedError(
                                "prefetching for multi source fields is not implemented. "
                                "Prefetch or select related within Prefetch queryset."
                            )
                        for prefetch in source_prefetch:
                            prefetch_attr = self._add_prefetch(prefetches=gathered_prefetches, prefetch=prefetch)
                            relations_sources[relation][source_key] = prefetch_attr
            else:
                raise NotImplementedError(
                    f"Sideloading with prefetch type {type(relation_prefetches)} has not been implemented"
                )

            if not relations_sources[relation]:
                raise ValueError("Source not found")

        return gathered_prefetches, relations_sources
