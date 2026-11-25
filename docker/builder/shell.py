import subprocess

# Error of a build step (message for the user)
class BuildError(Exception):
    pass

# Runs a command. Returns the CompletedProcess. All commands of the build go through this function (tests mock it).
def run(command,             # list of arguments
        cwd = None,          # working folder
        log = None,          # file to write stdout and stderr to (instead of capturing them)
        capture = False,     # capture stdout and stderr (text) in the result
        check = True,        # raise BuildError if the command fails
        env = None           # environment (None: inherited)
    ):
    if log:
        with open(log, "w") as f:
            result = subprocess.run(command, cwd = cwd, stdout = f, stderr = subprocess.STDOUT, env = env)
    elif capture:
        result = subprocess.run(command, cwd = cwd, capture_output = True, text = True, env = env)
    else:
        result = subprocess.run(command, cwd = cwd, env = env)

    if check and result.returncode != 0:
        raise BuildError(f"Command failed ({ result.returncode }): { ' '.join(command) }")

    return result
