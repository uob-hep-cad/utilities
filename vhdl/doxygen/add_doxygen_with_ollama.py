#!/usr/bin/env python3
"""
vhdl_doxygen.py — Add Doxygen comments to VHDL files using a local Ollama model.

Usage:
    python vhdl_doxygen.py input.vhd [output.vhd] [--model MODEL] [--inplace]

Examples:
    python vhdl_doxygen.py counter.vhd                      # writes counter_documented.vhd
    python vhdl_doxygen.py counter.vhd out.vhd              # writes to out.vhd
    python vhdl_doxygen.py counter.vhd --inplace            # overwrites input file
    python vhdl_doxygen.py counter.vhd --model codellama    # use a different model
"""

import argparse
import re
import sys
from pathlib import Path

try:
    import ollama
except ImportError:
    print("Error: ollama package not found. Install it with:  pip install ollama")
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
   --! @param   <name> Description of a generic or port
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
8. Return ONLY the commented VHDL code — no explanation, no markdown fences.
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
    # Split on top-level keywords that start a major block
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
    """Send VHDL code to Ollama and return the documented version."""
    chunks = chunk_vhdl(code)
    results = []

    for i, chunk in enumerate(chunks):
        if verbose:
            print(f"  Processing chunk {i + 1}/{len(chunks)} "
                  f"({len(chunk)} chars) ...", flush=True)

        user_msg = USER_PROMPT_TEMPLATE.format(filename=filename, code=chunk)

        response = ollama.chat(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_msg},
            ],
            options={"temperature": 0.1},  # low temp for deterministic output
        )

        result = response["message"]["content"].strip()

        # Strip accidental markdown code fences if the model adds them
        result = re.sub(r'^```[a-zA-Z]*\n?', '', result)
        result = re.sub(r'\n?```$', '', result)

        results.append(result)

    return "\n\n".join(results)


def derive_output_path(input_path: Path) -> Path:
    return input_path.with_name(input_path.stem + "_documented" + input_path.suffix)


def list_models() -> list[str]:
    try:
        return [m["name"] for m in ollama.list()["models"]]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add Doxygen comments to VHDL files using a local Ollama model.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("input",  help="Input .vhd / .vhdl file")
    parser.add_argument("output", nargs="?", help="Output file (optional)")
    parser.add_argument(
        "--model", default="mistral",
        help="Ollama model to use (default: mistral). "
             "Good choices: mistral, codellama, deepseek-coder",
    )
    parser.add_argument(
        "--inplace", action="store_true",
        help="Overwrite the input file instead of writing a new file",
    )
    parser.add_argument(
        "--list-models", action="store_true",
        help="List locally available Ollama models and exit",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print progress information",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # --list-models
    if args.list_models:
        models = list_models()
        if models:
            print("Available Ollama models:")
            for m in models:
                print(f"  {m}")
        else:
            print("No models found — is the Ollama daemon running?")
        return

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

    # Check model availability (non-fatal warning)
    available = list_models()
    if available and args.model not in available:
        print(f"\nWarning: model '{args.model}' not found locally.")
        print("Available models: " + ", ".join(available))
        print("Pull it first with:  ollama pull " + args.model)
        print()

    # Run
    print("\nAdding Doxygen comments...", flush=True)
    try:
        documented = add_doxygen(
            source,
            filename=input_path.name,
            model=args.model,
            verbose=args.verbose,
        )
    except ollama.ResponseError as exc:
        print(f"\nOllama error: {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"\nUnexpected error: {exc}")
        raise

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(documented, encoding="utf-8")
    print(f"\nDone. Documented file written to: {output_path}")


if __name__ == "__main__":
    main()
