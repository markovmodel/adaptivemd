from mongodb import StorableMixin


class Model(StorableMixin):
    """
    A wrapper to hold model data

    Attributes
    ----------
    data : dict of str : anything
        the data of the model
    """
    def __init__(self, data):
        super(Model, self).__init__()
        self.data = data
