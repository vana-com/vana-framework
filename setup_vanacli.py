# This script sets up the vanacli command by creating a script in the user's ~/bin directory
# and adding the directory to the PATH in the user's shell configuration file.
import os
import shutil
import subprocess

def setup_vanacli(project_dir):
    # Get the path to the user's home directory
    home_dir = os.path.expanduser("~")

    # Create the ~/bin directory if it doesn't exist
    bin_dir = os.path.join(home_dir, "bin")
    os.makedirs(bin_dir, exist_ok=True)

    # Create the vanacli script
    script_content = f'''#!/bin/bash

# Navigate to the project directory
cd "{project_dir}"

# Get the full path to the Poetry executable
POETRY_EXECUTABLE=$(which poetry)

# Run the Python script with the provided arguments
"$POETRY_EXECUTABLE" run python -c "from vana.cli import main; main()" "$@"
'''

    script_path = os.path.join(bin_dir, "vanacli")
    with open(script_path, "w") as file:
        file.write(script_content)

    # Make the script executable
    os.chmod(script_path, 0o755)

    # Add the ~/bin directory to the PATH if not already present
    shell_config_files = [
        os.path.join(home_dir, ".bashrc"),
        os.path.join(home_dir, ".bash_profile"),
        os.path.join(home_dir, ".zshrc")
    ]

    for config_file in shell_config_files:
        if os.path.exists(config_file):
            with open(config_file, "r") as file:
                config_content = file.read()

            if f'export PATH="{bin_dir}:$PATH"' not in config_content:
                with open(config_file, "a") as file:
                    file.write(f'\nexport PATH="{bin_dir}:$PATH"\n')

    print("vanacli command set up successfully!")

if __name__ == "__main__":
    project_dir = os.path.dirname(os.path.abspath(__file__))
    setup_vanacli(project_dir)