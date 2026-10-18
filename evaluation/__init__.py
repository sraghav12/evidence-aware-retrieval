"""Legacy public exports, loaded on demand to keep v2 offline imports light."""
__all__=['compute_match_metrics','run_benchmark','run_pipeline']


def __getattr__(name):
    if name=='compute_match_metrics':
        from evaluation.metrics import compute_match_metrics
        return compute_match_metrics
    if name in {'run_benchmark','run_pipeline'}:
        from evaluation import runner
        return getattr(runner,name)
    raise AttributeError(name)
