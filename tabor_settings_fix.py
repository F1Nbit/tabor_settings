""" Python script to automatically set player settings according to values found in PlayerSettings.json

    I don't know all that much about UE4 sav files, but from analyzing the data, it looks like only non-default
    settings are included in the file, which lines up with what I read online.
    Based on playing around I think the data structure for each boolean setting is likely:

    4 byte metadata - Key Name - 4 byte meta data - type - 8 bytes padding - value
    \x17\x00\x00\x00bUsingPhysicalGunstock\x00\r\x00\x00\x00BoolProperty\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00
     ^^^            ^^^^^^^^^^^^^^^^^^^^^^    ^^            ^^^^^^^^^^^^                                    ^^^^
     Decimal 23     22 character keyname      Decimal 13    12 characters                                   value 
                    + null-terminator                       + 1 null-terminator


"""

import glob
import json
import os
from pathlib import Path
import shutil
import time


DEFAULT_SETTINGS = {
    "bFullBodyIK": True,
    "bHoldCrouchToOpenMenu": True,
    "bUsingPhysicalGunstock": False
}

class SettingBytes:
    def __init__(self, key: str, data_type: str, value: any):
        self.key = key.encode('utf-8') + b'\x00'
        self.data_type = data_type.encode('utf-8') + b'\x00'
        self._padding = bytes([0] * 8)
        self._value = value

        # Precompute static values
        self.header = bytes([len(self.key), 0, 0, 0])
        self.type_metadata = bytes([len(self.data_type), 0, 0, 0])
        self.value = self._compute_value()

        # Precompute the full bytes representation
        self.bytes = (
            self.header +
            self.key +
            self.type_metadata +
            self.data_type +
            self._padding +
            self.value +
            bytes([0])  # Null-terminator
        )

    def _compute_value(self):
        """Compute the byte representation of the value based on its type."""
        if isinstance(self._value, (int, bool)):
            return bytes([self._value])
        elif isinstance(self._value, str):
            return self._value.encode('utf-8')
        elif isinstance(self._value, bytes):
            return self._value
        else:
            raise TypeError(f"Unsupported value type: {type(self._value)}")

def find_newest_settings_file(path):
    """ Find the newest PlayerSetting####.sav file in path """
    search_pattern = os.path.join(path, "PlayerSettings*.sav")
    
    # Find all matching files
    files = glob.glob(search_pattern)
    
    if not files:
        return None  # No matching files
    
    # Find the newest file by modification time
    newest_file = max(files, key=os.path.getmtime)
    return newest_file

def read_file(file_path):
    with open(file_path, 'rb') as file:
        return file.read()

def write_file(file_path, data):
    with open(file_path, 'wb') as file:
        file.write(data)


def locate_and_modify_player_settings(data, settings):
    """
    Locate and modify specified settings in the binary data.

    Args:
        data (bytes): The original binary data.
        settings (dict): A dictionary of settings to modify {"key": value}.

    Returns:
        bytes: Modified binary data.
    """
    file_modified = False
    modified_data = bytearray(data)
    data_anchor = 'BP_Ghosts_SettingsSave_C'.encode('utf-8') + b'\x00'
    insertion_index = data.find(data_anchor) + len(data_anchor)

    for key, value_data in settings.items():
        data_type = value_data['type']
        value = value_data['value']
        key_bytes = key.encode('utf-8') + b'\x00'  # Null-terminated string
        key_index = data.find(key_bytes)
        setting_bytes = SettingBytes(key, data_type, value)

        if key_index == -1:
            # Didn't find the key, so this is currently set to default
            if value != DEFAULT_SETTINGS[key]:
                # If desired value isn't the default insert this non-default value
                modified_data[insertion_index:insertion_index] = setting_bytes.bytes
                file_modified = True
        else:
            # We found a non-default value. For now I don't care, this means I set it at some point.
            # TODO delete it if desired setting is same as default
            # TODO overwrite it if desired setting isn't same as default or current value
            continue

    return bytes(modified_data) if file_modified else None

def main():
    file_dir = Path(os.environ.get("LOCALAPPDATA") + "\\GhostsOfTabor\\Saved\\SaveGames\\")
    file_name = find_newest_settings_file(file_dir)
    file_path = file_dir / file_name  # Original file

    output_path = file_dir / "Modified_PlayerSettings17122024.sav"  # Modified file

    # Read the original file
    data = read_file(file_path)

    # Modify the settings
    with open('PlayerSettings.json', "r") as fp:
        settings_to_modify = json.load(fp)
    modified_data = locate_and_modify_player_settings(data, settings_to_modify)

    if modified_data:
        # Backup old data
        timestamp = time.strftime("%Y%m%d%H%M%S")
        backup_file = f"{file_name}_{timestamp}.bak"
        shutil.copy(file_path, file_dir / backup_file)
        # Save the modified file
        write_file(file_path, modified_data)
        print(f"Modified file saved to {file_path}")

if __name__ == "__main__":
    main()
