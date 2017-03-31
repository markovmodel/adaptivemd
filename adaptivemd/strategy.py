from mongodb import StorableMixin
from event import event


class Strategy(StorableMixin):
    def __init__(self):
        super(Strategy, self).__init__()

    def __call__(self, project):
        project.add_event(self.default(project))

    @event
    def default(self, project):
        pass
