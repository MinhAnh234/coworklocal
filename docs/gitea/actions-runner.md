# Gitea Actions Runner

The repository includes `.gitea/workflows/ci.yaml`. Source import does not depend on a runner being online, but Pull Request checks do.

An administrator should:

1. Register an `act_runner` compatible with Gitea 1.27.1 at the instance, organization, or repository level.
2. Give it a label that can satisfy `runs-on: ubuntu-latest` (the common default label mapping is acceptable).
3. Ensure the runner can fetch the pinned major versions of `actions/checkout` and `actions/setup-python`, or mirror those actions internally.
4. Trigger the CI workflow and confirm both the syntax and routing test jobs complete.
5. Only then make the CI status check mandatory in stable-branch protection.

Do not weaken or ignore failing checks to obtain a green workflow. If no runner is available, keep the workflow committed and enforce the same commands during review.
