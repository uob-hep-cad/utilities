import google.generativeai as genai
import os
import glob
import time

# 1. Setup
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash-lite')

def document_vhdl_batch(directory_path):
    # Find all .vhd files in the directory
    vhdl_files = glob.glob(os.path.join(directory_path, "*.vhd"))
    
    if not vhdl_files:
        print("No VHDL files found in the directory.")
        return

    for file_path in vhdl_files:
        print(f"Processing: {os.path.basename(file_path)}...")
        
        with open(file_path, 'r') as f:
            vhdl_code = f.read()

        prompt = """\
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

VHDL Code:
{vhdl_code}
"""
        #f"Add Doxygen '--!' comments to this VHDL. Include @file header and @details for entities/ports. Return ONLY code:\n\n{vhdl_code}"

        try:
            response = model.generate_content(prompt)
            
            # Save to a 'documented' subfolder to keep things tidy
            output_dir = os.path.join(directory_path, "documented")
            os.makedirs(output_dir, exist_ok=True)
            
            output_path = os.path.join(output_dir, os.path.basename(file_path))
            
            with open(output_path, 'w') as f:
                clean_code = response.text.replace('```vhdl', '').replace('```', '').strip()
                f.write(clean_code)
            
            print(f"Done: {output_path}")
            
            # Brief pause to stay well within free tier rate limits
            time.sleep(60) 
            
        except Exception as e:
            print(f"Failed to process {file_path}: {e}")

if __name__ == "__main__":
    # Use '.' for current directory or provide a path
    document_vhdl_batch(".")
