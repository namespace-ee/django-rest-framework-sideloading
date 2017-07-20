=====
Usage
=====

To use drf-sideloading in a project, add it to your `INSTALLED_APPS`:

.. code-block:: python

    INSTALLED_APPS = (
        ...
        'drf_sideloading.apps.DrfSideloadingConfig',
        ...
    )

Add drf-sideloading's URL patterns:

.. code-block:: python

    from drf_sideloading import urls as drf_sideloading_urls


    urlpatterns = [
        ...
        url(r'^', include(drf_sideloading_urls)),
        ...
    ]
