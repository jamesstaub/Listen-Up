class PathTemplateResolver:
    """
    Resolves template strings used throughout job/step definitions.

    Templates may reference:
      - {{job_id}}
      - {{user_id}}
      - {{step_id}}
      - {{composite_name}}
      - {{steps.<step>.outputs.<key>}} for cross-step references

    This resolver produces *relative paths*; StorageManager turns them into
    absolute backend-specific paths.
    """

    def resolve(self, template: str, *, job, step=None) -> str:
        value = template

        # Basic fields
        value = value.replace("{{job_id}}", job.job_id)
        if job.user_id:
            value = value.replace("{{user_id}}", job.user_id)
        if step:
            value = value.replace("{{step_id}}", step.step_id)
            value = value.replace("{{composite_name}}", step.get_composite_name())

        # Cross-step references
        value = self._resolve_step_references(value, job)

        return value

    def _resolve_step_references(self, template: str, job) -> str:
        import re

        # Pattern: {{steps.<step_name>.outputs.<output_key>}}
        pattern = r"{{steps\.([a-zA-Z0-9_-]+)\.outputs\.([a-zA-Z0-9_-]+)}}"

        def replacer(match):
            step_name, output_key = match.groups()
            target = next((s for s in job.steps if s.step_id == step_name), None)
            if not target:
                raise ValueError(f"Unknown step '{step_name}' in template {template}")
            if output_key not in target.outputs:
                raise ValueError(f"Step '{step_name}' has no output '{output_key}'")
            return target.outputs[output_key]

        return re.sub(pattern, replacer, template)

    def resolve_all_outputs(self, step, job):
        """
        Produces a new dict where all output templates of a step
        are fully resolved and safe to pass to CommandResolver.
        """
        return {k: self.resolve(v, job=job, step=step) for k, v in step.outputs.items()}

    def resolve_all_inputs(self, step, job):
        return {k: self.resolve(v, job=job, step=step) for k, v in step.inputs.items()}
