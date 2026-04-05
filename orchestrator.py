import logging

from agent_framework import (
    AgentExecutorRequest,
    AgentExecutorResponse,
    Case,
    Default,
    Executor,
    Message,
    WorkflowBuilder,
    WorkflowContext,
    handler,
)

from agents import create_agents

logger = logging.getLogger(__name__)

MAX_REVISIONS = 2


def _get_all_text(msg: Message) -> str:
    """Extract ALL text from a message, including thinking/reasoning content."""
    parts = []
    for content in msg.contents:
        if content.type == "text" and content.text:
            parts.append(content.text)
        elif content.type == "text_reasoning" and content.text:
            parts.append(content.text)
    return " ".join(parts)


class ReviewGate(Executor):
    """Inspects the reviewer's verdict and forwards the conversation.

    Tracks revision count. After MAX_REVISIONS failed reviews, auto-approves
    to prevent infinite loops (especially with thinking models that may not
    produce visible "APPROVED" text).
    """

    def __init__(self) -> None:
        super().__init__(id="review_gate")
        self._revision_count = 0

    @handler
    async def handle(
        self,
        response: AgentExecutorResponse,
        ctx: WorkflowContext[AgentExecutorRequest],
    ) -> None:
        self._revision_count += 1

        # Check if reviewer approved (search all content types)
        approved = False
        if response.full_conversation:
            last_msg = response.full_conversation[-1]
            all_text = _get_all_text(last_msg).lower()
            if "approved" in all_text and "revision" not in all_text:
                approved = True

        # Auto-approve after max revisions to prevent infinite loop
        if not approved and self._revision_count > MAX_REVISIONS:
            logger.info(
                f"Auto-approving after {self._revision_count} revisions "
                "(max revisions reached)"
            )
            approved = True

        # Always send full_conversation because AgentExecutor clears its
        # internal cache after each run. Without the full history the next
        # agent would receive an empty message list and crash.
        await ctx.send_message(
            AgentExecutorRequest(
                messages=response.full_conversation,
                should_respond=True,
            )
        )

    def _check_approved(self) -> bool:
        """Returns True if we should route to QA."""
        return self._revision_count > MAX_REVISIONS


class Finish(Executor):
    """Captures QA output and yields the full conversation as the workflow result."""

    def __init__(self) -> None:
        super().__init__(id="finish")

    @handler
    async def handle(
        self,
        response: AgentExecutorResponse,
        ctx: WorkflowContext[None, list[Message]],
    ) -> None:
        await ctx.yield_output(response.full_conversation)


def build_planning_workflow():
    """Build the deterministic planning workflow.

    Graph:
        input(str) -> PM -> Architect -> Developer -> Reviewer -> review_gate
                                            ^                        |
                                            |   (revision needed)    |
                                            +------------------------+
                                                  (approved) |
                                                      QA -> finish -> output
    """
    pm, architect, developer, reviewer, qa = create_agents()

    review_gate = ReviewGate()
    finish = Finish()

    def _is_approved(request: AgentExecutorRequest) -> bool:
        """Route to QA if approved or max revisions exceeded."""
        # Check the review_gate's internal state (auto-approve after max revisions)
        if review_gate._check_approved():
            return True
        if not request.messages:
            return False
        last_msg = request.messages[-1]
        all_text = _get_all_text(last_msg).lower()
        return "approved" in all_text and "revision" not in all_text

    workflow = (
        WorkflowBuilder(start_executor=pm, max_iterations=30, name="software-planner")
        # Linear pipeline
        .add_edge(pm, architect)
        .add_edge(architect, developer)
        .add_edge(developer, reviewer)
        .add_edge(reviewer, review_gate)
        # Conditional routing: approved → QA, otherwise → Developer (loop)
        .add_switch_case_edge_group(
            review_gate,
            cases=[
                Case(condition=_is_approved, target=qa),
                Default(target=developer),
            ],
        )
        # QA terminates the workflow
        .add_edge(qa, finish)
        .build()
    )

    return workflow
