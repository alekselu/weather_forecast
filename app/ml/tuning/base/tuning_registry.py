class TuningRegistry:
    def __init__(self):
        self.results = {}

    def register(
        self,
        result,
    ):
        key = (
            result.model_type,
            result.target,
            result.city,
        )
        self.results[key] = result

    def get_best(
        self,
        target,
        city=None,
    ):
        candidates = []
        for key, result in self.results.items():
            _, r_target, r_city = key
            if r_target == target and r_city == city:
                candidates.append(result)
        return min(
            candidates,
            key=lambda r: r.best_score,
        )
