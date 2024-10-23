import copy
import importlib
import re
from itertools import chain
from typing import Dict, Optional, Union, Set, List

from django.db import models
from django.db.models import Prefetch
from django.db.models.fields.related_descriptors import (
    ForwardManyToOneDescriptor,
    ForwardOneToOneDescriptor,
    ReverseOneToOneDescriptor,
    ReverseManyToOneDescriptor,
)
from django.db.models.sql.where import WhereNode, AND
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import RetrieveModelMixin, ListModelMixin
from rest_framework.response import Response
from rest_framework.serializers import ListSerializer

from drf_sideloading.serializers import SideLoadableSerializer


RELATION_DESCRIPTORS = [
    ForwardManyToOneDescriptor,
    ForwardOneToOneDescriptor,
    ReverseOneToOneDescriptor,
    ReverseManyToOneDescriptor,
]


def contains_where_node(existing_node: WhereNode, new_node: WhereNode) -> bool:
    """
    Checks if the existing_node contains the new_node.
    It will no check OR conditions however!
    """
    if not isinstance(new_node, WhereNode):
        raise ValueError("new_node has to be a WhereNode instance")
    if not isinstance(existing_node, WhereNode):
        return False
    if not set(new_node.children) - set(existing_node.children):  # all new node children applied
        return True
    if existing_node.connector == AND:
        for child_node in existing_node.children:
            exists = contains_where_node(child_node, new_node)
            if exists:
                return True
    return False


class SideloadableRelationsMixin(object):
    sideloading_query_param_name = "sideload"
    sideloading_serializer_class = None
    primary_field_name: str = None
    sideloadable_fields: Dict = {}
    user_defined_prefetches: Dict = {}
    primary_field = None
    sideloadable_field_sources: Dict = {}
    if importlib.util.find_spec("drf_spectacular") is not None:
        from drf_sideloading.schema import SideloadingAutoSchema

        # note: if required, the user can overwrite the schema
        schema = SideloadingAutoSchema()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.check_sideloading_serializer_class(self.sideloading_serializer_class)

    def initialize_serializer(self, request):
        sideloading_serializer_class = self.get_sideloading_serializer_class(request=request)
        self.check_sideloading_serializer_class(sideloading_serializer_class)

        # sideloadable fields
        self.sideloadable_fields = copy.deepcopy(sideloading_serializer_class._declared_fields)
        self.primary_field_name = sideloading_serializer_class.Meta.primary
        self.primary_field = self.sideloadable_fields.pop(self.primary_field_name)
        self.primary_model = self.primary_field.child.Meta.model

        # fetch sideloading sources and prefetches
        self.user_defined_prefetches = getattr(sideloading_serializer_class.Meta, "prefetches", {})
        self.sideloadable_field_sources = self.get_sideloading_field_sources()

    def get_source_from_prefetch(self, prefetches: Union[str, List, Dict]):
        if isinstance(prefetches, str):
            return prefetches
        if isinstance(prefetches, Prefetch):
            return prefetches.to_attr or prefetches.prefetch_through
        elif isinstance(prefetches, dict):
            if any(isinstance(v, dict) for v in prefetches.values()):
                raise ValueError("Can't find source to_attr from dict.")
            return {k: self.get_source_from_prefetch(v) for k, v in prefetches.items()}
        elif isinstance(prefetches, list):
            if not all(isinstance(v, (str, Prefetch)) for v in prefetches):
                raise ValueError("Can't find source to_attr from list not containing only strings or prefetches.")
            return sorted(self.get_source_from_prefetch(v) for v in prefetches)[0]

    def get_sideloading_field_sources(self) -> Dict:
        if not self.sideloadable_fields:
            raise ValueError("Sideloading serializer has not been initialized")

        relations_sources = {}
        for relation, field in self.sideloadable_fields.items():
            relation_prefetches = self.user_defined_prefetches.get(relation)
            if isinstance(relation_prefetches, dict) and any(isinstance(v, dict) for v in relation_prefetches.values()):
                relation_prefetches = {
                    k: self._clean_prefetches(field=field, relation=relation, value=v)
                    for k, v in relation_prefetches.items()
                }

            sideloadable_field_source = field.child.source

            # its a MultiSource field, fetch values from sources defined with prefetches.
            if isinstance(relation_prefetches, dict) and sideloadable_field_source:
                raise ValueError("Multi source field with source defined in serializer.")

            if relation_prefetches:
                data_source = self.get_source_from_prefetch(relation_prefetches)
            elif sideloadable_field_source:
                data_source = sideloadable_field_source
            elif isinstance(getattr(self.primary_model, relation), tuple(RELATION_DESCRIPTORS)):
                data_source = relation
            else:
                raise ValueError(f"Could not determine source for field '{relation}'.")

            relations_sources[relation] = data_source

        return relations_sources

    def get_relations_to_sideload(self, request) -> Optional[Dict]:
        """
        Parse query param and take validated names

        :param sideload_parameter string
        :return valid relation names list

        comma separated relation names may contain invalid or unusable characters.
        This function finds string match between requested names and defined relation in view

        new:

        response changed to dict as the sources for multi source fields must be selectable.

        """
        if request.method != "GET":
            return None

        if self.sideloading_query_param_name not in request.query_params:
            return None

        sideload_parameter = request.query_params[self.sideloading_query_param_name]
        if not sideload_parameter:
            return None
            # raise ValidationError({self.sideloading_query_param_name: [_(f"'{relation}' Can not be blank.")]})

        # This fetches the correct serializer and prepares sideloadable_fields ect.
        self.initialize_serializer(request=request)

        relations_to_sideload = {}
        for param in re.split(r",\s*(?![^\[\]]*\])", sideload_parameter):
            if "[" in param:
                fieldname, sources_str = param.split("[", 1)
                if not sources_str.strip("]"):
                    msg = _(f"'{fieldname}' source can not be empty.")
                    raise ValidationError({self.sideloading_query_param_name: [msg]})
                relations = set(sources_str.strip("]").split(","))
            else:
                fieldname = param
                relations = None

            if fieldname not in self.sideloadable_fields:
                msg = _(f"'{fieldname}' is not one of the available choices.")
                raise ValidationError({self.sideloading_query_param_name: [msg]})

            # check for source selection. select all if nothing given
            if isinstance(self.user_defined_prefetches.get(fieldname), dict):
                source_relations = sorted(self.user_defined_prefetches[fieldname].keys())
                if relations is None:
                    relations = source_relations
                else:
                    # Check if all requested sources are defined
                    invalid_sources = set(relations) - set(source_relations)
                    if invalid_sources:
                        msg = _(f"'{fieldname}' sources {', '.join(invalid_sources)} are not defined.")
                        raise ValidationError({self.sideloading_query_param_name: [msg]})
            elif relations:
                msg = _(f"'{fieldname}' is not a multi source field.")
                raise ValidationError({self.sideloading_query_param_name: [msg]})

            # everything checks out.
            relations_to_sideload[fieldname] = relations

        return relations_to_sideload

    def check_sideloading_serializer_class(self, sideloading_serializer_class):
        if not sideloading_serializer_class:
            raise ValueError(f"'{self.__class__.__name__}' sideloading_serializer_class not found")
        if not issubclass(sideloading_serializer_class, SideLoadableSerializer):
            raise ValueError(
                f"'{self.__class__.__name__}' sideloading_serializer_class must be a SideLoadableSerializer subclass"
            )
        sideloading_serializer_class.check_setup()

    def get_sideloading_serializer(self, *args, **kwargs):
        """
        Return the sideloading_serializer instance that should be used for serializing output.
        """
        sideloading_serializer_class = self.get_sideloading_serializer_class()
        kwargs["context"] = self.get_sideloading_serializer_context()
        return sideloading_serializer_class(*args, **kwargs)

    def get_sideloading_serializer_class(self, request=None):
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

    def get_sideloadable_queryset(self, prefetch):
        if isinstance(prefetch, str):
            model = self.primary_model
            for x in prefetch.split("__"):
                descriptor = getattr(model, x)
                if isinstance(descriptor, ForwardManyToOneDescriptor):
                    model = descriptor.field.remote_field.model
                elif isinstance(descriptor, ForwardOneToOneDescriptor):
                    model = descriptor.field.remote_field.model
                elif isinstance(descriptor, ReverseOneToOneDescriptor):
                    model = descriptor.related.related_model
                elif isinstance(descriptor, ReverseManyToOneDescriptor):
                    model = descriptor.field.model
                else:
                    raise NotImplementedError(f"Descriptor {descriptor.__class__.__name__} has not been implemented")
            return model.objects.all()
        elif isinstance(prefetch, Prefetch):
            return prefetch.queryset
        else:
            raise NotImplementedError(f"finding queryset for prefetch type {type(prefetch)} has not been implemented")

    def add_sideloading_prefetches(self, queryset, request, relations_to_sideload):
        # Iterate over the prefetches of the original queryset and modify them
        view_prefetches = {}
        for prefetch in queryset._prefetch_related_lookups:
            self._add_prefetch(prefetches=view_prefetches, prefetch=prefetch, request=request)
        original_prefetches = [v for k, v in sorted(view_prefetches.items())]

        # find applicable prefetches
        gathered_prefetches = self._get_relevant_prefetches(
            relations_to_sideload=relations_to_sideload,
            gathered_prefetches=view_prefetches,
            request=request,
        )

        # replace prefetches if any change made
        prefetches = [v for k, v in sorted(gathered_prefetches.items())]
        if prefetches != original_prefetches:
            if original_prefetches:
                queryset = queryset.prefetch_related(None)
            queryset = queryset.prefetch_related(*prefetches)
        return queryset

    # modified DRF methods

    def retrieve(self, request, *args, **kwargs):
        if not isinstance(self, RetrieveModelMixin):
            # The viewset does not have RetrieveModelMixin and therefore the method is not allowed
            return self.http_method_not_allowed(request, *args, **kwargs)

        relations_to_sideload = self.get_relations_to_sideload(request=request)
        if not relations_to_sideload:
            try:
                return super().retrieve(request=request, *args, **kwargs)
            except AttributeError as exc:
                if "super' object has no attribute 'retrieve'" in exc.args[0]:
                    # self.retrieve() method was not declared before this mixin.
                    # Make sure the SideloadableRelationsMixin is defined higher than RetrieveModelMixin.
                    return self.http_method_not_allowed(request, *args, **kwargs)
                raise exc

        # return object with sideloading serializer
        queryset = self.get_sideloadable_object_as_queryset(
            request=request,
            relations_to_sideload=relations_to_sideload,
        )
        sideloadable_page = self.get_sideloadable_page_from_queryset(
            queryset=queryset,
            relations_to_sideload=relations_to_sideload,
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

        relations_to_sideload = self.get_relations_to_sideload(request=request)
        if not relations_to_sideload:
            try:
                return super().list(request=request, *args, **kwargs)
            except AttributeError as exc:
                if "super' object has no attribute 'list'" in exc.args[0]:
                    # self.list() method was not declared before this mixin.
                    # Make sure the SideloadableRelationsMixin is defined higher than ListModelMixin.
                    return self.http_method_not_allowed(request, *args, **kwargs)
                raise exc

        # After this `relations_to_sideload` is safe to use
        queryset = self.get_queryset()
        queryset = self.add_sideloading_prefetches(
            queryset=queryset,
            request=request,
            relations_to_sideload=relations_to_sideload,
        )
        queryset = self.filter_queryset(queryset)

        # Create page
        page = self.paginate_queryset(queryset)
        if page is not None:
            sideloadable_page = self.get_sideloadable_page(
                page=page,
                relations_to_sideload=relations_to_sideload,
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
                relations_to_sideload=relations_to_sideload,
            )
            serializer = self.get_sideloading_serializer(
                instance=sideloadable_page,
                relations_to_sideload=relations_to_sideload,
                context={"request": request},
            )
            return Response(serializer.data)

    def get_sideloadable_page_from_queryset(self, queryset, relations_to_sideload: Dict):
        """
        Populates page with sideloaded data by collecting ids form sideloaded values and then making into a query
        """

        if not relations_to_sideload:
            raise ValueError("relations_to_sideload is required")
        # this works wonders, but can't be used when page is paginated...
        sideloadable_page = {self.primary_field_name: queryset}

        for relation, source_keys in relations_to_sideload.items():
            field = self.sideloadable_fields[relation]
            field_source = field.child.source
            source_model = field.child.Meta.model
            relation_key = field_source or relation

            related_ids = set()
            sideloadable_field_source = self.sideloadable_field_sources.get(relation)
            if isinstance(sideloadable_field_source, dict):
                for src_key, src in sideloadable_field_source.items():
                    if src_key in source_keys or source_keys is None or src_key == "__all__":
                        related_ids |= set(queryset.values_list(src, flat=True))
            else:
                prefetch_key = field_source or self.sideloadable_field_sources[relation]
                prefetch_object = next(
                    (x for x in queryset._prefetch_related_lookups if getattr(x, "prefetch_to", None) == prefetch_key),
                    None,
                )
                if prefetch_key in queryset._prefetch_related_lookups:
                    related_ids |= set(queryset.values_list(prefetch_key, flat=True))
                elif prefetch_object:
                    if prefetch_object.queryset:
                        # performance thing?
                        # related_ids |= set(
                        #     prefetch_object.queryset.filter(
                        #         id__in=(queryset.values_list(prefetch_key, flat=True))
                        #     ).values_list("id", flat=True)
                        # )

                        for obj in queryset.all():
                            prefetched_data = getattr(obj, prefetch_key)
                            if prefetched_data.__class__.__name__ in [
                                "ManyRelatedManager",
                                "RelatedManager",
                            ]:
                                related_ids |= set(prefetched_data.values_list("id", flat=True))
                            elif isinstance(prefetched_data, models.Model):
                                related_ids.add(prefetched_data.id)
                            elif isinstance(prefetched_data, list):
                                try:
                                    related_ids |= set(x.id for x in prefetched_data)
                                except AttributeError:
                                    related_ids |= set(prefetched_data)
                            elif prefetched_data:
                                raise ValueError("???")

                    else:
                        related_ids |= set(queryset.values_list(prefetch_key, flat=True))
                else:
                    raise ValueError(f"No prefetch for {prefetch_key} found!")

            sideloadable_page[relation_key] = source_model.objects.filter(id__in=related_ids)

        return sideloadable_page

    def get_sideloadable_page(self, page, relations_to_sideload: Dict):
        """
        Populates page with sideloaded data by collecting distinct values form sideloaded data
        """
        sideloadable_page = {self.primary_field_name: page}
        for relation, source_keys in relations_to_sideload.items():
            field = self.sideloadable_fields[relation]
            field_source = field.child.source
            relation_key = field_source or relation

            if not isinstance(field, ListSerializer):
                raise RuntimeError("SideLoadable field '{}' must be set as many=True".format(relation))

            if relation not in sideloadable_page:
                sideloadable_page[relation_key] = set()

            if isinstance(self.sideloadable_field_sources.get(relation), dict):
                # Multi source relation
                for src_key, source_prefetch in self.sideloadable_field_sources[relation].items():
                    if not source_keys or src_key in source_keys:
                        sideloadable_page[relation_key] |= self.filter_related_objects(
                            related_objects=page, lookup=source_prefetch
                        )
            else:
                sideloadable_page[relation_key] |= self.filter_related_objects(
                    related_objects=page, lookup=field_source or self.sideloadable_field_sources[relation]
                )

        return sideloadable_page

    def get_sideloadable_object_as_queryset(self, request, relations_to_sideload):
        """
        mimics DRF original method get_object()
        Returns the object the view is displaying with sideloaded models prefetched.

        You may want to override this if you need to provide non-standard
        queryset lookups.  Eg if objects are referenced using multiple
        keyword arguments in the url conf.
        """
        # Add prefetches if applicable
        queryset = self.get_queryset()
        queryset = self.add_sideloading_prefetches(
            queryset=queryset,
            request=request,
            relations_to_sideload=relations_to_sideload,
        )
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

    def filter_related_objects(self, related_objects, lookup: Optional[str]) -> Set:
        current_lookup, remaining_lookup = lookup.split("__", 1) if "__" in lookup else (lookup, None)
        lookup_values = [
            getattr(r, current_lookup) for r in related_objects if getattr(r, current_lookup, None) is not None
        ]

        if lookup_values:
            if lookup_values[0].__class__.__name__ in ["ManyRelatedManager", "RelatedManager"]:
                # FIXME: apply filtering here!
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

    def _gather_all_prefetches(self) -> Dict:
        """
        this method finds all prefetches required and checks if they are correctly defined
        """
        cleaned_prefetches = {}

        if not self.sideloadable_fields:
            raise ValueError("Sideloading serializer has not been initialized")

        # find prefetches for all sideloadable relations
        for relation, field in self.sideloadable_fields.items():
            user_prefetches = self.user_defined_prefetches.get(relation)
            field_source = field.child.source
            if relation in self.user_defined_prefetches and not user_prefetches:
                raise ValueError(f"prefetches for field '{relation}' have been left empty")
            elif not user_prefetches:
                if field_source:
                    # default to field source if not defined by user
                    cleaned_prefetches[relation] = [field_source]
                elif getattr(self.primary_field.child.Meta.model, relation, None):
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

    def add_sideloading_prefetch_filter(self, source, queryset, request):
        """
        This method is intended to e overwritten in case the user wants to implement
        their own filters based on the related model or the relationship to the base model

        source - string path to the value that is sideloded.
        queryset - QuerySet that you can add filtering to

        Example:

        add_sideloading_prefetch_filter(self, source, queryset, request):
            if source == "model1__relation1":
                return queryset.filter(is_active=True), True
            if hasattr(queryset, "readable"):
                return queryset.readable(user=request.user), True
            return queryset, False

        """

        return queryset, False

    def _add_sideloading_filter(self, prefetch: Union[str, Prefetch], request) -> Union[str, Prefetch]:
        # fetch sideloadable source and queryset
        prefetch_source = self.get_source_from_prefetch(prefetches=prefetch)
        prefetch_queryset = self.get_sideloadable_queryset(prefetch)
        filtered_queryset, added = self.add_sideloading_prefetch_filter(
            source=prefetch_source, queryset=prefetch_queryset, request=request
        )
        if added:
            filter_node = self.add_sideloading_prefetch_filter(
                source=prefetch_source, queryset=prefetch_queryset.model.objects.all(), request=request
            )[0].query.where
            if filter_node:  # check if any filtering is actually applied
                if isinstance(prefetch, str):
                    # Replace string prefetch with a filtered one
                    prefetch = Prefetch(lookup=prefetch, queryset=filtered_queryset)
                elif isinstance(prefetch, Prefetch):
                    # add filters if not already applied
                    if not contains_where_node(existing_node=prefetch_queryset.query.where, new_node=filter_node):
                        prefetch.queryset = filtered_queryset
                else:
                    raise NotImplementedError(
                        f"Adding filters to prefetch type {type(prefetch)} has not been implemented"
                    )

        return prefetch

    def _add_prefetch(self, prefetches: Dict, prefetch: Union[str, Prefetch], request) -> str:
        # add prefetch to prefetches dict and return the prefetch_attr
        if not isinstance(prefetch, (str, Prefetch)):
            raise ValueError(f"Adding prefetch of type '{type(prefetch)}' has not been implemented")
        if isinstance(prefetch, str) and len(prefetch) == 1:
            raise ValueError("single letter prefetches are not allowed")

        prefetch = self._add_sideloading_filter(prefetch=prefetch, request=request)

        prefetch_attr = self.get_source_from_prefetch(prefetch)
        existing_prefetch = prefetches.get(prefetch_attr)
        if not existing_prefetch:
            prefetches[prefetch_attr] = prefetch
        elif isinstance(existing_prefetch, str):
            if isinstance(prefetch, str):
                if prefetch != existing_prefetch:
                    raise ValueError("Got different string prefetches to the same attribute name")
            elif isinstance(prefetch, Prefetch):
                if prefetch.queryset.query.where:
                    raise ValueError(
                        f"Can't add filtered Prefetch '{prefetch_attr}'. Existing prefetch does not have filters. "
                        "APIView might have an unfiltered prefetch_related that sideloading is trying to filter."
                    )
                # Do nothing, as no filters where applied, leave the prefetch as a string
            else:
                raise NotImplementedError(f"overwriting existing string prefetch wit type {type(prefetch)}")
        elif isinstance(existing_prefetch, Prefetch):
            if isinstance(prefetch, str):
                if existing_prefetch.queryset.query.where:
                    raise ValueError(
                        f"Can't add non-filtered prefetch '{prefetch_attr}'. Existing Prefetch has filters applied. "
                        "Sideloading serializer tries to apply a non-filtered prefetch to a previously filtered "
                        "prefetch"
                    )
                # Don't make any changes as the Prefetch does not have filters
            elif isinstance(prefetch, Prefetch):
                if prefetch.queryset.model != existing_prefetch.queryset.model:
                    raise ValueError(
                        f"Can't add filtered Prefetch '{prefetch_attr}'. Existing Prefetch has a different model."
                    )
                if set(prefetch.queryset.query.where.children) != set(existing_prefetch.queryset.query.where.children):
                    raise ValueError(
                        f"Can't add filtered Prefetch '{prefetch_attr}'. "
                        "Existing Prefetch has different filters applied. "
                        "Check that sideloading serializer and view prefetch_related values don't clash"
                    )
                # Don't make any changes as the filters have to match each other
            else:
                raise NotImplementedError(f"overwriting existing Prefetch with type {type(prefetch)}")
        else:
            raise NotImplementedError(f"Adding prefetch of type '{type(prefetch)}' has not been implemented")

        return prefetch_attr

    def _get_relevant_prefetches(self, relations_to_sideload: Dict, request, gathered_prefetches: Dict = None) -> Dict:
        """
        Collects all relevant prefetches and returns
        compressed prefetches and sources per relation to be used later.
        """

        if gathered_prefetches is None:
            gathered_prefetches = {}

        # cleaned prefetches
        cleaned_prefetches = self._gather_all_prefetches()

        if not relations_to_sideload:
            raise ValueError("'relations_to_sideload' is a required argument")
        if not cleaned_prefetches:
            raise ValueError("'cleaned_prefetches' is a required argument")

        for relation, requested_sources in relations_to_sideload.items():
            relation_prefetches = cleaned_prefetches.get(relation)
            if requested_sources:
                for source in requested_sources:
                    for source_prefetch in relation_prefetches[source]:
                        self._add_prefetch(prefetches=gathered_prefetches, prefetch=source_prefetch, request=request)
            elif isinstance(relation_prefetches, dict):
                for source_prefetches in relation_prefetches.values():
                    for source_prefetch in source_prefetches:
                        self._add_prefetch(prefetches=gathered_prefetches, prefetch=source_prefetch, request=request)
            else:
                for relation_prefetch in relation_prefetches:
                    self._add_prefetch(prefetches=gathered_prefetches, prefetch=relation_prefetch, request=request)

        return gathered_prefetches
