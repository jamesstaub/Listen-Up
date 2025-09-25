# step_state_machine.py
from transitions import Machine
from shared.modules.job.enums.job_step_state_enum import JobStepState
from shared.modules.job.models.job_step import JobStep

class StepStateMachine:
    """
    Wraps a JobStep to provide a state machine and execution logic.
    """
    def __init__(self, step: JobStep):
        self.step = step
        self.machine = Machine(model=self.step, states=[s.value for s in JobStepState], initial=self.step.state)
        self.machine.add_transition("initialize", JobStepState.PENDING.value, JobStepState.INITIALIZING.value)
        self.machine.add_transition("run", JobStepState.INITIALIZING.value, JobStepState.RUNNING.value)
        self.machine.add_transition("upload", JobStepState.RUNNING.value, JobStepState.UPLOADING.value)
        self.machine.add_transition("complete", JobStepState.UPLOADING.value, JobStepState.COMPLETE.value)
        self.machine.add_transition("fail", '*', JobStepState.FAILED.value)

    def execute(self, manifest=None, asset_manager=None):
        """
        Example sequence:
        initialize -> run -> upload -> complete
        """
        try:
            self.step.initialize()
            self.step.run()
            self.step.upload()
            self.step.complete()
        except Exception:
            self.step.fail()
