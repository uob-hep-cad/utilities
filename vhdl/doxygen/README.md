# Utilities to add Doxygen comments to VHDL code

- check_gemini_models.py - Checks what models are available from Gemini
- add_doxygen_with_gemini_batch.py - The script that Gemini produces
- add_doxygen_with_gemini.py  - The script that Gemini produces, that reads all files in directory
- add_doxygen_with_ollama.py - First go with ChatGPT asking for an OLlama interface
- add_doxygen_with_gemini_from_claude.py - Used Claude to produce Python that uses Gemini - set the environment varialble GEMINIA_API_KEY first. This is the code that is most advanced.
- gen_doxygen_script.py - generates a Bash script that executes add_doxygen_with_gemini_from_claude.py on each VHDL file in a directory tree



