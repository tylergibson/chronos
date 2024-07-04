import json
import os
import shutil

from chronos.script import Script
from chronos.config import CHRONOS
from chronos.util import for_uid
from chronos.venv import rename_env
from chronos.metadata import Session, Script as ScriptModel, Log


def run(arguments, event):
    arguments = json.loads(arguments)
    old_name = arguments["old_name"]
    new_name = arguments["new_name"]

    session = Session()

    # Convert names to UIDs
    old_uid = for_uid(old_name)
    new_uid = for_uid(new_name)

    old_script = Script(old_uid)
    new_script = Script(new_uid)

    old_script_path = os.path.join(CHRONOS, "scripts", old_uid)
    new_script_path = os.path.join(CHRONOS, "scripts", new_uid)

    # Rename script folder
    if os.path.isdir(old_script_path):
        os.rename(old_script_path, new_script_path)
    else:
        raise FileNotFoundError(f"Script folder {old_script_path} does not exist.")

    # Rename virtual environment
    rename_env(old_uid, new_uid)

    # Rename script file
    old_script_file = os.path.join(new_script_path, f"{old_uid}.py")
    new_script_file = os.path.join(new_script_path, f"{new_uid}.py")
    if os.path.isfile(old_script_file):
        os.rename(old_script_file, new_script_file)
    else:
        raise FileNotFoundError(f"Script file {old_script_file} does not exist.")

    # Rename execute.sh file
    execute_sh_path = os.path.join(new_script_path, "execute.sh")
    if os.path.isfile(execute_sh_path):
        with open(execute_sh_path, "r") as file:
            data = file.read()
        data = data.replace(old_uid, new_uid)
        with open(execute_sh_path, "w") as file:
            file.write(data)

    # Rename pip install.sh file
    install_sh_path = os.path.join(new_script_path, "install.sh")
    if os.path.isfile(install_sh_path):
        with open(install_sh_path, "r") as file:
            data = file.read()
        data = data.replace(old_uid, new_uid)
        with open(install_sh_path, "w") as file:
            file.write(data)

    # Update logs
    logs = session.query(Log).filter(Log.script == old_script.uid).all()
    for log in logs:
        log.script = new_script.uid
        session.add(log)

    # Update script metadata
    script_metadata = session.query(ScriptModel).filter(ScriptModel.uid == old_uid).first()
    if script_metadata:
        script_metadata.uid = new_uid
        script_metadata.name = new_name
        session.add(script_metadata)
    else:
        raise ValueError(f"Script metadata for {old_uid} does not exist.")

    session.commit()
    session.close()

    event.trigger("action_complete", {"action": "rename", "old_uid": old_uid, "new_uid": new_uid})
    event.trigger("script_renamed", {"old_uid": old_uid, "new_uid": new_uid})

    return {"old_uid": old_uid, "new_uid": new_uid}

# Example usage
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Rename a script")
    parser.add_argument("old_name", type=str, help="The current name of the script")
    parser.add_argument("new_name", type=str, help="The new name for the script")
    args = parser.parse_args()

    arguments = json.dumps({"old_name": args.old_name, "new_name": args.new_name})
    
    class Event:
        def trigger(self, action, data):
            print(f"Event triggered: {action} with data {data}")
    
    event = Event()
    result = run(arguments, event)
    print(f"Renamed script from {result['old_uid']} to {result['new_uid']}")
