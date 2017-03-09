# Decide what to do with the current model

from analysis import DoAnalysis
from mongodb import StorableMixin


class Brain(StorableMixin):
    def __init__(self, engine, analyzer):
        super(Brain, self).__init__()
        self.engine = engine
        self.analyzer = analyzer

    def execute(self, project):
        # add events
        map(project.add_event, self.get_events(project))

        # submit initial tasks
        project.submit(self.initial_tasks(project))

    def initial_tasks(self, project):
        return project.new_trajectory(project.engine['pdb'], 10, number=2)

    def get_events(self, project):
        event_analysis = DoAnalysis(
            when=project.on_ntraj(range(5, 100, 5)),
            modeller=project['modeller']
        )

        return [
            event_analysis
        ]
