from mongodb import StorableMixin


class Model(StorableMixin):
    """
    A wrapper to hold model data

    This uses a special grid storage to save models larger than 16MB

    Attributes
    ----------
    data : dict of str : anything
        the data of the model
    """
    def __init__(self, data):
        super(Model, self).__init__()
        self.data = data

    def __getitem__(self, item):
        return self.data[item]

    def __getattr__(self, item):
        if item in self.data:
            return self.data[item]