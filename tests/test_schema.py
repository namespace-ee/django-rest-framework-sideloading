import importlib.util

import pytest
from django.test import override_settings

from drf_sideloading.mixins import SideloadableRelationsMixin

spectacular_installed = importlib.util.find_spec("drf_spectacular") is not None


def test_schema_support_follows_drf_spectacular_availability():
    """The library must import cleanly whether or not drf-spectacular is installed."""
    assert ("schema" in vars(SideloadableRelationsMixin)) is spectacular_installed


@pytest.mark.skipif(spectacular_installed, reason="drf-spectacular is installed")
def test_schema_module_is_not_imported_without_drf_spectacular():
    import sys

    assert "drf_sideloading.schema" not in sys.modules


@pytest.mark.skipif(not spectacular_installed, reason="requires drf-spectacular")
def test_mixin_uses_the_sideloading_schema():
    from drf_sideloading.schema import SideloadingAutoSchema

    assert isinstance(vars(SideloadableRelationsMixin)["schema"], SideloadingAutoSchema)


@pytest.mark.skipif(not spectacular_installed, reason="requires drf-spectacular")
@override_settings(REST_FRAMEWORK={"DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema"})
def test_sideload_parameter_is_documented():
    from drf_spectacular.generators import SchemaGenerator

    schema = SchemaGenerator().get_schema(request=None, public=True)
    parameters = schema["paths"]["/productlistonly/"]["get"]["parameters"]
    sideload = next(p for p in parameters if p["name"] == "sideload")

    assert sideload["in"] == "query"
    assert set(sideload["schema"]["items"]["enum"]) == {
        "backup_suppliers",
        "categories",
        "combined_suppliers",
        "main_suppliers",
        "metadata",
        "partners",
    }
    examples = {v["summary"]: v["value"] for v in sideload["examples"].values()}
    assert examples["Regular sideloading"] == "categories,main_suppliers"
    assert examples["Multi source sideloading for combined_suppliers"] == (
        "combined_suppliers[suppliers,backup_supplier]"
    )
