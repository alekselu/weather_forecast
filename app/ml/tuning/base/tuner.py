from abc import ABC, abstractmethod


class BaseTuner(ABC):
    @abstractmethod
    def tune(
        self,
        X,
        y,
    ):
        pass
