#
# Gemini API Key 01
# projects/677356087174
# 677356087174
#

import google.generativeai as genai
import os

# 1. Setup your API Key
# It is best practice to use environment variables
os.environ["GOOGLE_API_KEY"] = "YOUR_GEMINI_API_KEY"
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

def document_vhdl_file(input_filename):
    """Reads a VHDL file, adds Doxygen comments via Gemini, and saves it."""
    
    # Initialize the model
    model = genai.GenerativeModel('gemini-1.5-flash')

    # Read the VHDL source code
    try:
        with open(input_filename, 'r') as f:
            vhdl_code = f.read()
    except FileNotFoundError:
        print(f"Error: The file '{input_filename}' was not found.")
        return

    # Construct the prompt
    prompt = f"""
    You are an expert hardware engineer. Please add Doxygen-style comments to the following VHDL code.
    
    Requirements:
    1. Use the '--!' prefix for Doxygen comments.
    2. Add a file header with @file, @brief, and @details.
    3. Document entities, architectures, ports, and generics using @details, @param (for generics), and @brief.
    4. Ensure the output is ONLY the code. Do not include any markdown block markers like ```vhdl or explanations.
    5. Maintain the original indentation and logic of the code.

    VHDL Code:
    {vhdl_code}
    """

    print(f"Sending '{input_filename}' to Gemini for documentation...")
    
    # Generate the response
    response = model.generate_content(prompt)
    
    if response.text:
        output_filename = f"documented_{input_filename}"
        with open(output_filename, 'w') as f:
            # Cleaning up any potential markdown formatting the AI might have added
            clean_code = response.text.replace('```vhdl', '').replace('```', '').strip()
            f.write(clean_code)
        
        print(f"Success! Documented file saved as: {output_filename}")
    else:
        print("Error: Gemini failed to return a response.")

if __name__ == "__main__":
    # Replace with your actual VHDL file name
    file_to_process = "my_design.vhd" 
    document_vhdl_file(file_to_process)
    
