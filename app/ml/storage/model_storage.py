from pathlib import Path


class ModelStorage:

    BASE_PATH = Path("models")

    @classmethod
    def get_model_path(
        cls,
        city,
        target,
        model_type,
    ):
        path = cls.BASE_PATH / city / target

        path.mkdir(
            parents=True,
            exist_ok=True,
        )

        return path / f"{model_type}.pkl"
