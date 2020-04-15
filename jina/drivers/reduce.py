from . import BaseDriver


class MergeDriver(BaseDriver):
    """Merge the routes information from multiple envelopes into one """

    def __call__(self, *args, **kwargs):
        # take unique routes by service identity
        routes = {(r.pod + r.pod_id): r for m in self.prev_msgs for r in m.envelope.routes}
        self.msg.envelope.ClearField('routes')
        self.msg.envelope.routes.extend(
            sorted(routes.values(), key=lambda x: (x.start_time.seconds, x.start_time.nanos)))


class MergeTopKDriver(MergeDriver):
    """Merge the topk results from multiple messages into one and sorted

    Useful in indexer sharding (i.e. ``--replicas > 1``)
    """

    def __init__(self, level: str, *args, **kwargs):
        """

        :param level: merge level "chunk" or "doc", or "all"
        """
        super().__init__(*args, **kwargs)
        self.merge_level = level

    def __call__(self, *args, **kwargs):
        if self.merge_level == 'chunk':
            for _d_id, _doc in enumerate(self.req.docs):
                for _c_id, _chunk in enumerate(_doc.chunks):
                    _flat_topk = [k for r in self.prev_reqs for k in r.docs[_d_id].chunks[_c_id].topk_results]
                    _chunk.ClearField('topk_results')
                    _chunk.topk_results.extend(sorted(_flat_topk, key=lambda x: x.score.value))
        elif self.merge_level == 'doc':
            for _d_id, _doc in enumerate(self.req.docs):
                _flat_topk = [k for r in self.prev_reqs for k in r.docs[_d_id].topk_results]
                _doc.ClearField('topk_results')
                _doc.topk_results.extend(sorted(_flat_topk, key=lambda x: x.score.value))
        elif self.merge_level == 'all':
            for _d_id, _doc in enumerate(self.req.docs):
                _flat_topk = [k for r in self.prev_reqs for k in r.docs[_d_id].topk_results]
                _doc.ClearField('topk_results')
                _doc.topk_results.extend(sorted(_flat_topk, key=lambda x: x.score.value))

                for _c_id, _chunk in enumerate(_doc.chunks):
                    _flat_topk = [k for r in self.prev_reqs for k in r.docs[_d_id].chunks[_c_id].topk_results]
                    _chunk.ClearField('topk_results')
                    _chunk.topk_results.extend(sorted(_flat_topk, key=lambda x: x.score.value))

        else:
            raise TypeError(f'level={self.merge_level} is not supported, must choose from "chunk" or "doc" ')

        super().__call__(*args, **kwargs)


class MergeTopKChunksDriver(MergeTopKDriver):
    """Merge topk results at chunk level

    Complexity: D x C x K x R

    where:
        - D is the number of queries
        - C is the number of chunks per query
        - K is the top-k
        - R is the number of shards (i.e. ``--replicas``)
    """

    def __init__(self, level: str = 'chunk', *args, **kwargs):
        super().__init__(level, *args, **kwargs)


class MergeTopKDocsDriver(MergeTopKDriver):
    """Merge topk results at doc level

    Complexity: D x K x R

    where:
        - D is the number of queries
        - K is the top-k
        - R is the number of shards (i.e. ``--replicas``)
    """

    def __init__(self, level: str = 'doc', *args, **kwargs):
        super().__init__(level, *args, **kwargs)
