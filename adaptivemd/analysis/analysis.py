# Create compute units for various simulation tools

from adaptivemd.generator import PythonRPCTaskGenerator
from adaptivemd.event import Event


class Analysis(PythonRPCTaskGenerator):
    """
    A generator for tasks that represent analysis of trajectories
    """
    pass


class DoAnalysis(Event):
    def __init__(self, when, modeller):
        super(DoAnalysis, self).__init__(when)

        self.do(modeller.task_run_msm)
