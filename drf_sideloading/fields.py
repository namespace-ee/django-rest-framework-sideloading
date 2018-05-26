
class SideloadableRelationField(object):
    serializer = None
    source = None
    prefetch = None

    def __init__(self, serializer, source=None, prefetch=None):
        self.serializer = serializer
        self.source = source
        self.prefetch = prefetch

    def get_prefetches(self):
        """
        made as a separate method in case we want to try and find the relations automatically?

        :return: prefetch_relations
        :rtype: list
        """
        if isinstance(self.prefetch, str):
            self.prefetch = [self.prefetch]
        elif isinstance(self.prefetch, list) and all(isinstance(v, str) for v in self.prefetch):
            return self.prefetch
        else:
            raise Exception("All sideloadable relation prefetches must be defined as list of strings")
