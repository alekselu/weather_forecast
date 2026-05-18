class Forecast:
    def __init__(self, model_selector):
        self.model_selector = model_selector

    def predict(self, X):
        return self.model_selector.predict(X)

    def retrain(self, X, y):
        self.model_selector.train(X, y)
