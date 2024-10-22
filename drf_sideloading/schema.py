from typing import Dict, Union
from django.utils.translation import gettext_lazy as _

from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiExample,
    OpenApiTypes,
)
from drf_spectacular.openapi import AutoSchema


class SideloadingAutoSchema(AutoSchema):
    override_parameters = []

    def get_override_parameters(self):
        if self.method == "GET":
            # return self.override_parameters
            self.view.initialize_serializer(request=getattr(self.view, "request", None))
            sideloading_keys_sources: Dict[str, Union[str, Dict[str, str]]] = self.view.get_sideloading_field_sources()
            sideloading_keys = list(k for k, v in sideloading_keys_sources.items() if isinstance(v, str))
            multi_source_sideloading_items = {
                k: list(v.keys()) for k, v in sideloading_keys_sources.items() if isinstance(v, dict)
            }
            examples = []
            if sideloading_keys:
                examples.append(
                    OpenApiExample(
                        name=_("Regular sideloading"),
                        value=",".join(sideloading_keys[:2]),
                        request_only=True,
                    )
                )
            for k, v in multi_source_sideloading_items.items():
                examples.append(
                    OpenApiExample(
                        name=_(f"Multi source sideloading for {k}"),
                        value=f"{k}[{','.join(v)}]",
                        request_only=True,
                    )
                )
            return [
                OpenApiParameter(
                    name="sideload",
                    type=OpenApiTypes.STR,
                    location=OpenApiParameter.QUERY,
                    many=True,
                    description=_(
                        "This option allows you to fetch related obejcts for all of the relations with a signle query. "
                        "Multi-source sideloadable fields can be filtered by the sources by declaring the required "
                        "sources in square brackets after the sideloading key. All available Mutli-source fields will "
                        "have an example provided with all available sources. The comma separated sources can be "
                        "ommited with the square brackets if all sources are to be sideloaded."
                    ),
                    enum=sideloading_keys_sources.keys(),
                    examples=examples,
                )
            ]
        return []
