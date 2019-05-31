from __future__ import unicode_literals

import re
from collections import defaultdict

import six
import copy

from itertools import chain

from rest_framework.relations import PrimaryKeyRelatedField, HyperlinkedRelatedField, SlugRelatedField, \
    HyperlinkedIdentityField, ManyRelatedField
from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.response import Response
from rest_framework.serializers import ListSerializer, ModelSerializer

from drf_sideloading.renderers import BrowsableAPIRendererWithoutForms
from drf_sideloading.serializers import SideLoadableSerializer


class SideloadableRelationsMixin(object):
    query_param_name = "sideload"
    flat_param_name = "flat"
    sideloading_serializer_class = None
    _primary_field_name = None
    _sideloadable_fields = None
    relations_to_sideload = None
    related_keys_for_flattening = None
    relations_to_pop = []

    def __init__(self, **kwargs):
        self.check_sideloading_serializer_class()
        self._primary_field_name = self.get_primary_field_name()
        self._sideloadable_fields = self.get_sideloadable_fields()
        self._prefetches = self.get_sideloading_prefetches()
        self.related_keys_for_flattening = None
        self.relations_to_pop = []
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
                    raise RuntimeError("Sideloadable prefetch values must be presented either as a list or a string")
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

    def flatmap_sideloaded_serializer_fields(self):
        fields_mapping = {}

        def flatmap_serializer_fields(serializer, original_tail, tail):
            for field in serializer.fields:
                field_serializer = serializer.fields.get(field)
                source = getattr(field_serializer, "source", None)
                flat_source = (source or field).replace('.', '__').replace('*', field)

                new_tail = "{}__{}".format(tail or '', flat_source).lstrip("__")
                new_original_tail = "{}__{}".format(original_tail or '', flat_source).lstrip("__")

                if isinstance(field_serializer, ListSerializer):
                    field_serializer = field_serializer.child
                if isinstance(field_serializer, ModelSerializer):
                    flatmap_serializer_fields(field_serializer, new_original_tail, new_tail)
                else:
                    fields_mapping[new_tail] = new_original_tail

        for field, field_serializer in self.sideloading_serializer_class._declared_fields.items():
            if field == self._primary_field_name:
                flatmap_serializer_fields(field_serializer.child, original_tail=field, tail=None)
            else:
                source = field_serializer.source or field
                flatmap_serializer_fields(field_serializer.child, original_tail=field, tail=source)

        return fields_mapping

    def add_related_keys_for_flattening(self):
        relation_fields = []
        self.related_keys_for_flattening = defaultdict(dict)
        # add relations to be able to flatten the data
        # TODO: find a way to remove these after flattening, in case they are not in the "allowed_fields"

        primary_serializer = self.sideloading_serializer_class._declared_fields[self._primary_field_name].child
        for relation in self.relations_to_sideload:
            sl_related_serializer = self.sideloading_serializer_class._declared_fields[relation].child
            primary_key = sl_related_serializer.source or relation

            # find the relation key that the primary model points to (id, url, slug ect.. )
            relation_field = primary_serializer.fields[primary_key]

            if isinstance(relation_field, ManyRelatedField):
                relation_field = relation_field.child_relation

            if isinstance(relation_field, PrimaryKeyRelatedField):
                relation_key = relation_field.pk_field or relation_field.queryset.model._meta.pk.name
                if relation_key not in sl_related_serializer.Meta.fields:
                    for field, field_serializer in sl_related_serializer.fields.items():
                        if field_serializer.source == relation_key:
                            relation_key = field
                            break
                    else:
                        raise RuntimeError("PrimaryKey related Sideloadable serializers must have a primary key field!")

            elif isinstance(relation_field, SlugRelatedField):
                relation_key = relation_field.slug_field
                if relation_key not in sl_related_serializer.Meta.fields:
                    for field, field_serializer in sl_related_serializer.fields.items():
                        if field_serializer.source == relation_key:
                            relation_key = field
                            break
                    else:
                        raise RuntimeError("SlugRelated related Sideloadable serializers must have a field with value!")

            elif isinstance(relation_field, HyperlinkedRelatedField):
                for field, field_serializer in sl_related_serializer.fields.items():
                    if isinstance(field_serializer, HyperlinkedIdentityField):
                        relation_key = field
                        break
                else:
                    raise RuntimeError(
                        "Hyperlink related Sideloadable serializers must have a HyperlinkedIdentityField"
                    )
            else:
                raise RuntimeError("No relation found between primary and sideloadable serializers.")

            relation_fields.append("{}__{}".format(self._primary_field_name, primary_key))
            relation_fields.append("{}__{}".format(relation, relation_key))
            self.related_keys_for_flattening[relation][primary_key] = relation_key

        return relation_fields

    def get_serializer(self, *args, **kwargs):
        # in order to use SelectableFieldsMixin, we must be able to pass "allowed_fields" through to the serializer

        sideloading = kwargs.pop("sideloading", False)
        flatten = kwargs.pop("flatten", False)

        if sideloading:
            required_fields = None
            if flatten:
                # add relations to be able to flatten the data after
                required_fields = self.add_related_keys_for_flattening()

            allowed_fields = kwargs.pop('allowed_fields', None)
            if allowed_fields:
                # rename fields to be the same as in the default serializer.
                fields_mapping = self.flatmap_sideloaded_serializer_fields()
                kwargs["allowed_fields"] = [fields_mapping[field] for field in allowed_fields if
                                            field in fields_mapping]
                if required_fields:
                    kwargs["required_fields"] = required_fields
                    self.relations_to_pop = set(kwargs["required_fields"]) - set(kwargs["allowed_fields"])

            # get context
            context = self.get_serializer_context()
            context.update(kwargs.get('context', {}))
            kwargs['context'] = context
            try:
                return self.sideloading_serializer_class(*args, **kwargs)
            except KeyError:
                kwargs.pop('allowed_fields')
                return self.sideloading_serializer_class(*args, **kwargs)
        return super(SideloadableRelationsMixin, self).get_serializer(*args, **kwargs)

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
            serializer = self.get_serializer(
                instance=sideloadable_page,
                sideloading=True,
                flatten=flatten,
                fields_to_load=[self._primary_field_name] + list(self.relations_to_sideload),
                context={"request": request},
            )
            if flatten:
                return self.get_paginated_response(self.flatten_sideloaded_data(serialized_data=serializer.data))
            return self.get_paginated_response(serializer.data)
        else:
            sideloadable_page = self.get_sideloadable_page_from_queryset(queryset)
            serializer = self.get_serializer(
                instance=sideloadable_page,
                sideloading=True,
                flatten=flatten,
                fields_to_load=[self._primary_field_name] + list(self.relations_to_sideload),
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
        if not self.related_keys_for_flattening:
            raise RuntimeError('related_keys_for_flattening is missing')

        # self.related_keys_for_flattening[relation][primary_key] = relation_key

        for relation, reference_keys in self.related_keys_for_flattening.items():
            for data in serialized_data[relation]:
                for primary_key, sideloaded_ref in reference_keys.items():
                    if "{}__{}".format(relation, sideloaded_ref) in self.relations_to_pop:
                        key = data.pop(sideloaded_ref)
                    else:
                        key = data[sideloaded_ref]
                    sideloaded_data[relation][key] = self.flatten_data(data, primary_key)

        for object in primary_objects:
            for relation, reference_keys in self.related_keys_for_flattening.items():
                for primary_key, sideloaded_ref in reference_keys.items():
                    primary_relation_value = object.pop(primary_key)
                    if isinstance(primary_relation_value, list):
                        for i, relation_value in enumerate(primary_relation_value):
                            val = sideloaded_data[relation][relation_value]
                            xxx = {
                                re.sub(r'^{}'.format(relation), '{}__{}'.format(relation, i), k, 1): v
                                for k, v in val.items()
                            }
                            object.update(xxx)
                    else:
                        object.update(sideloaded_data[relation][primary_relation_value])
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


class SelectableDataMixin(object):
    fields_param_name = "fields"

    def __init__(self, **kwargs):
        self._allowed_fields = []
        super(SelectableDataMixin, self).__init__(**kwargs)

    def initialize_request(self, request, *args, **kwargs):
        request = super(SelectableDataMixin, self).initialize_request(request=request, *args, **kwargs)
        allowed_fields = request.query_params.get(self.fields_param_name)
        if allowed_fields:
            self._allowed_fields = allowed_fields.split(",")
        return request

    def get_serializer(self, *args, **kwargs):
        if self._allowed_fields:
            kwargs["allowed_fields"] = self._allowed_fields
        return super(SelectableDataMixin, self).get_serializer(*args, **kwargs)
