import asyncio
import os

from agent_framework import AgentResponseUpdate, Message

from orchestrator import build_planning_workflow

DEFAULT_PROJECT_IDEA = (
    "Build a REST API for a task management app with user auth, "
    "CRUD operations, and real-time notifications"
)


async def run():
    print("=" * 60)
    print("  Software Project Planner — Multi-Agent System")
    print("  (Microsoft Agent Framework)")
    print("=" * 60)

    user_input = input("\nEnter your project idea (or press Enter for demo):\n> ").strip()
    if not user_input:
        user_input = DEFAULT_PROJECT_IDEA
        print(f"\nUsing default: {user_input}")

    print("\n" + "-" * 60)
    print("Starting multi-agent planning session...")
    print("-" * 60 + "\n")

    workflow = build_planning_workflow()

    # Stream the planning session with real-time output
    conversation = None
    current_agent = None
    stream_open = False

    async for event in workflow.run(user_input, stream=True):
        if event.type == "output" and isinstance(event.data, AgentResponseUpdate):
            # Print agent name header when switching to a new agent
            if current_agent != event.executor_id:
                if stream_open:
                    print("\n")
                    stream_open = False
                print(f"---------- {event.executor_id} ----------")
                current_agent = event.executor_id

            # Show text content (normal output)
            if event.data.text:
                print(event.data.text, end="", flush=True)
                stream_open = True
            else:
                # Fallback: check for thinking/reasoning content
                # (qwen3.5 and other thinking models produce text_reasoning)
                for content in event.data.contents:
                    if content.type == "text_reasoning" and content.text:
                        print(content.text, end="", flush=True)
                        stream_open = True

        elif event.type == "output" and isinstance(event.data, list):
            # Final output — the full conversation
            if stream_open:
                print("\n")
                stream_open = False
            conversation = event.data

    if stream_open:
        print("\n")

    print("\n" + "=" * 60)
    print("  Planning Session Complete")
    print("=" * 60)

    if not conversation:
        print("No output produced.")
        return

    # Count agent messages
    agent_msgs = [m for m in conversation if isinstance(m, Message) and m.role == "assistant"]
    print(f"\nTotal agent messages: {len(agent_msgs)}")

    # Ask user to confirm code generation
    print("\n" + "-" * 60)
    confirm = input("Do you agree with this plan and want to generate the codebase? (yes/no): ").strip().lower()
    if confirm not in ("yes", "y"):
        print("Codebase generation skipped. Goodbye!")
        return

    output_dir = input("Enter the folder path to store the generated source code:\n> ").strip()
    if not output_dir:
        print("No folder path provided. Aborting.")
        return

    output_dir = os.path.abspath(os.path.expanduser(output_dir))

    if os.path.exists(output_dir) and os.listdir(output_dir):
        overwrite = input(f"Folder '{output_dir}' is not empty. Continue anyway? (yes/no): ").strip().lower()
        if overwrite not in ("yes", "y"):
            print("Aborted.")
            return

    os.makedirs(output_dir, exist_ok=True)

    print("\n" + "-" * 60)
    print("Generating codebase from the plan...")
    print("-" * 60 + "\n")

    from codegen import generate_codebase

    file_count = await generate_codebase(conversation, output_dir)

    print("\n" + "=" * 60)
    print(f"  Code Generation Complete — {file_count} files created")
    print(f"  Output: {output_dir}")
    print("=" * 60)


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
