import os
import re

from agent_framework import Agent, Message

from config import create_code_client, get_code_options

CODEGEN_SYSTEM_MESSAGE = """\
You are a Code Generator agent. You receive a complete software project plan \
(requirements, architecture, implementation plan, code snippets, API design) \
and you MUST generate the actual source code files for the project.

CRITICAL RULES:
1. Generate ALL files needed for a working project based on the plan.
2. Each file MUST be wrapped in this exact format:

###FILE: relative/path/to/file.ext###
(file content here)
###ENDFILE###

3. Generate files in dependency order (configs first, then models, then services, etc.).
4. Include ALL necessary files: source code, configuration files, build files, \
   dockerfiles, .gitignore, README, etc.
5. Write production-ready code — not pseudocode or placeholders.
6. Follow the tech stack, architecture, and patterns from the plan exactly.
7. Do NOT include explanations outside of file blocks. ONLY output file blocks.
8. If there are too many files to generate in one response, end with:
   ###CONTINUE###
   and you will be prompted to continue generating the remaining files.
9. When all files are generated, end with:
   ###DONE###
"""

FILE_PATTERN = re.compile(
    r"###FILE:\s*(.+?)\s*###\n(.*?)###ENDFILE###",
    re.DOTALL,
)

CODEBLOCK_PATTERN = re.compile(r"^```[a-zA-Z0-9]*\n?", re.MULTILINE)
CODEBLOCK_END_PATTERN = re.compile(r"\n?```\s*$", re.MULTILINE)


def _strip_markdown_codeblocks(content: str) -> str:
    """Remove markdown code fences wrapping file content."""
    stripped = content.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        stripped = CODEBLOCK_PATTERN.sub("", stripped, count=1)
        stripped = CODEBLOCK_END_PATTERN.sub("", stripped, count=1)
        return stripped.strip() + "\n"
    return content


def _build_plan_summary(conversation: list[Message]) -> str:
    """Concatenate the planning session into a single prompt for the code generator."""
    skip_agents = {"reviewer", "review_gate", "finish"}
    parts = []
    for msg in conversation:
        name = msg.author_name or msg.role
        if name.lower() in skip_agents:
            continue
        # Get regular text first, fall back to reasoning/thinking content
        text = msg.text or ""
        if not text:
            reasoning_parts = [
                c.text for c in msg.contents
                if c.type == "text_reasoning" and c.text
            ]
            text = " ".join(reasoning_parts)
        if text:
            parts.append(f"=== {name.upper()} ===\n{text}")
    return "\n\n".join(parts)


async def generate_codebase(conversation: list[Message], output_dir: str) -> int:
    """Generate project files from the planning conversation.

    Returns the number of files written.
    """
    plan_text = _build_plan_summary(conversation)

    print("\n" + "=" * 60)
    print("  Plan Summary (sent to code generator)")
    print("=" * 60)
    print(plan_text[:500] + "..." if len(plan_text) > 500 else plan_text)
    print("=" * 60 + "\n")

    code_client = create_code_client()
    coder = Agent(
        client=code_client,
        name="coder",
        instructions=CODEGEN_SYSTEM_MESSAGE,
        default_options=get_code_options(),
    )

    prompt = (
        "Here is the complete project plan. Generate ALL source code files now.\n\n"
        f"{plan_text}\n\n"
        "Generate all files using the ###FILE: path### ... ###ENDFILE### format. "
        "When finished, end with ###DONE###."
    )

    # Use session for multi-turn continuation
    session = coder.create_session()
    all_text = ""

    # Initial generation
    print("Generating files...")
    response = await coder.run(prompt, session=session)
    all_text += response.text or ""

    # Continue if needed (up to 5 continuations)
    for i in range(5):
        if "###DONE###" in all_text:
            break
        if "###CONTINUE###" not in all_text:
            break
        print(f"Continuing generation (round {i + 2})...")
        response = await coder.run(
            "Continue generating the remaining files. When finished, end with ###DONE###.",
            session=session,
        )
        all_text += response.text or ""

    # Extract and write files
    files = [
        (m.group(1).strip(), _strip_markdown_codeblocks(m.group(2)))
        for m in FILE_PATTERN.finditer(all_text)
    ]

    written = 0
    for filepath, content in files:
        filepath = filepath.lstrip("/").lstrip("\\")
        if ".." in filepath:
            print(f"  Skipping suspicious path: {filepath}")
            continue

        full_path = os.path.join(output_dir, filepath)
        os.makedirs(os.path.dirname(full_path) or ".", exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  Created: {filepath}")
        written += 1

    return written
