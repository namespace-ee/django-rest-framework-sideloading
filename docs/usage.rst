=====
Usage
=====


Import siedloading mixin


.. literalinclude:: ../example/products/views.py
    :lines: 3


Use in existing viewset by inheriting and defining `sideloadable_relations`


.. literalinclude:: ../example/products/views.py
    :lines: 8-20



Request::

    GET /product/?sideload=categories,partners,suppliers
