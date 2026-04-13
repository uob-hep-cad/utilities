#!/usr/bin/env python3
"""
vhdl_doxygen.py — Add Doxygen comments to VHDL files using the Google Gemini API.

Requires a Gemini API key (free tier available at https://aistudio.google.com/):
    export GEMINI_API_KEY="AIza..."

Usage:
    python vhdl_doxygen.py input.vhd [output.vhd] [--model MODEL] [--inplace]

Examples:
    python vhdl_doxygen.py counter.vhd                              # writes counter_documented.vhd
    python vhdl_doxygen.py counter.vhd out.vhd                      # writes to out.vhd
    python vhdl_doxygen.py counter.vhd --inplace                    # overwrites input file
    python vhdl_doxygen.py counter.vhd --model gemini-2.5-pro       # use Pro instead of Flash
"""

import argparse
import os
import re
import sys
from pathlib import Path

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Error: google-genai package not found. Install it with:  pip install google-genai")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an expert VHDL engineer. Your task is to add Doxygen-style comments to
VHDL source code. Follow these rules strictly:

1. Use Doxygen comment syntax compatible with the DoxyVHDL extension:
   --! for single-line Doxygen comments
   --! @brief   Short one-line description
   --! @details Longer explanation (optional, only when genuinely useful)
   --! @param   <n> Description of a generic or port
   --! @return  Description of what the entity produces (if applicable)

2. Add a file-level header block before the first 'library' or 'entity' line:
   --! @file    <filename>
   --! @brief   <short description>
   --! @details <longer description if warranted>

3. Add a comment block immediately before each ENTITY declaration describing:
   - @brief what the entity does
   - @param for every GENERIC (with type and default if present)
   - @param for every PORT (with direction and type)

4. Add a --! @brief comment before each ARCHITECTURE, PROCESS, and FUNCTION/PROCEDURE.

5. Add brief --! inline comments on signal, variable, and constant declarations
   that are not self-explanatory.

6. Do NOT remove or alter any existing code — only add comments.
7. Do NOT add redundant comments that merely restate the identifier name.
8. Include author name and date as doxygen comments
9. Return ONLY the commented VHDL code — no explanation, no markdown fences.
"""

USER_PROMPT_TEMPLATE = """\
Add Doxygen comments to the following VHDL code.
Filename: {filename}

{code}
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def chunk_vhdl(code: str, max_chars: int = 6000) -> list[str]:
    """
    Split large VHDL files into chunks that respect entity/architecture
    boundaries so the model has coherent context per call.
    """
    boundary = re.compile(
        r'(?=^\s*(?:library|use|entity|architecture|package)\b)',
        re.IGNORECASE | re.MULTILINE,
    )
    parts = boundary.split(code)
    chunks, current = [], ""
    for part in parts:
        if len(current) + len(part) > max_chars and current:
            chunks.append(current)
            current = part
        else:
            current += part
    if current:
        chunks.append(current)
    return chunks or [code]


def add_doxygen(code: str, filename: str, model: str, verbose: bool) -> str:
    """Send VHDL code to Gemini and return the documented version."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.")
        print("Get a free key at https://aistudio.google.com/ then run:")
        print("  export GEMINI_API_KEY='AIza...'")
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    chunks = chunk_vhdl(code)
    results = []

    for i, chunk in enumerate(chunks):
        if verbose:
            print(f"  Processing chunk {i + 1}/{len(chunks)} "
                  f"({len(chunk)} chars) ...", flush=True)

        user_msg = USER_PROMPT_TEMPLATE.format(filename=filename, code=chunk)

        response = client.models.generate_content(
            model=model,
            contents=user_msg,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.1,
                max_output_tokens=8192,
            ),
        )

        result = response.text.strip()

        # Strip accidental markdown code fences if the model adds them
        result = re.sub(r'^```[a-zA-Z]*\n?', '', result)
        result = re.sub(r'\n?```$', '', result)

        results.append(result)

    return "\n\n".join(results)


def derive_output_path(input_path: Path) -> Path:
    return input_path.with_name(input_path.stem + "_documented" + input_path.suffix)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add Doxygen comments to VHDL files using the Google Gemini API.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("input",  help="Input .vhd / .vhdl file")
    parser.add_argument("output", nargs="?", help="Output file (optional)")
    parser.add_argument(
        "--model", default="gemini-2.5-flash",
        help="Gemini model to use (default: gemini-2.5-flash). "
             "Other options: gemini-2.5-pro, gemini-2.0-flash",
    )
    parser.add_argument(
        "--inplace", action="store_true",
        help="Overwrite the input file instead of writing a new file",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print progress information",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Validate input
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: file not found: {input_path}")
        sys.exit(1)
    if input_path.suffix.lower() not in {".vhd", ".vhdl"}:
        print(f"Warning: '{input_path.suffix}' is not a recognised VHDL extension.")

    # Determine output path
    if args.inplace:
        output_path = input_path
    elif args.output:
        output_path = Path(args.output)
    else:
        output_path = derive_output_path(input_path)

    # Read source
    source = input_path.read_text(encoding="utf-8", errors="replace")
    if not source.strip():
        print("Error: input file is empty.")
        sys.exit(1)

    print(f"Model  : {args.model}")
    print(f"Input  : {input_path}  ({len(source)} chars)")
    print(f"Output : {output_path}")

    # Run
    print("\nAdding Doxygen comments...", flush=True)
    try:
        documented = add_doxygen(
            source,
            filename=input_path.name,
            model=args.model,
            verbose=args.verbose,
        )
    except Exception as exc:
        msg = str(exc)
        if "API_KEY_INVALID" in msg or "401" in msg:
            print("\nError: Invalid API key. Check your GEMINI_API_KEY.")
        elif "quota" in msg.lower() or "429" in msg:
            print("\nError: Quota exceeded. Wait a moment and try again, "
                  "or upgrade your plan at https://aistudio.google.com/")
        else:
            print(f"\nGemini API error: {exc}")
        sys.exit(1)

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(documented, encoding="utf-8")
    print(f"\nDone. Documented file written to: {output_path}")


if __name__ == "__main__":
    main()
