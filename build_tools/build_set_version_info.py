import re
import datetime
import os

COMPANY_NAME = "Hamid R. Yari"


VERSION_FILE = "../VERSION"
LICENSE_FILE = "../LICENSE"

VERSION_INFO_OUTPUT_FILE = "../build_version_details.txt"

PRODUCT_NAME = "Media Catalog Telegram Bot"
FILE_DESCRIPTION = "Telegram Bot for Media Catalog Management"
INTERNAL_NAME = "MediaCatalogBot"
ORIGINAL_FILENAME = "MediaCatalogBot.exe"

VERSION_INFO_TEMPLATE = """# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={FILEVERS_TUPLE}, prodvers={PRODVERS_TUPLE}, mask=0x3f, flags=0x0,
    OS=0x40004, fileType=0x1, subtype=0x0
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'{COMPANY_NAME}'),
         StringStruct(u'FileDescription', u'{FILE_DESCRIPTION}'),
         StringStruct(u'FileVersion', u'{VERSION_STR_FULL}'),
         StringStruct(u'InternalName', u'{INTERNAL_NAME}'),
         StringStruct(u'LegalCopyright', u'{COPYRIGHT_STR}'),
         StringStruct(u'OriginalFilename', u'{ORIGINAL_FILENAME}'),
         StringStruct(u'ProductName', u'{PRODUCT_NAME}'),
         StringStruct(u'ProductVersion', u'{VERSION_STR_FULL}')])
      ]
    ),
    VarFileInfo([VarStruct(u'Translation', [0x0409, 1200])])
  ]
)
"""


def get_version():
    try:
        with open(VERSION_FILE, "r") as f:
            version_str = f.read().strip()
        match = re.match(r"(\d+)\.(\d+)\.(\d+)(?:\.(\d+))?", version_str)
        if not match:
            raise ValueError("Version string format is invalid.")
        groups = match.groups()
        major, minor, patch = int(groups[0]), int(groups[1]), int(groups[2])
        build = int(groups[3]) if groups[3] else 0
        return f"{major}.{minor}.{patch}.{build}", (major, minor, patch, build)
    except Exception as e:
        print(
            f"Warning: Error reading version file '{VERSION_FILE}': {e}. Defaulting version.")
        now = datetime.datetime.now()
        build_num_fallback = int(
            f"{now.year % 100}{now.month:02d}{now.day:02d}{now.hour:02d}{now.minute:02d}")
        return f"0.0.0.{build_num_fallback}", (0, 0, 0, build_num_fallback)


def get_copyright_notice(company_name_param):
    current_year = datetime.datetime.now().year
    license_type = "Unknown License"
    try:
        with open(LICENSE_FILE, "r", encoding="utf-8") as f:
            content = f.read(200).lower()
            if "gnu general public license" in content:
                if "version 3" in content:
                    license_type = "GPLv3"
                elif "version 2" in content:
                    license_type = "GPLv2"
                else:
                    license_type = "GPL"
            elif "mit license" in content:
                license_type = "MIT License"
    except FileNotFoundError:
        print(f"Warning: {LICENSE_FILE} not found.")
    except Exception as e:
        print(
            f"Warning: Could not determine license from {LICENSE_FILE}: {e}.")
    return f"© {current_year} {company_name_param}. Licensed under {license_type}."


def main():
    if COMPANY_NAME == "Your Name/Company":
        print("!!! IMPORTANT: Please update 'COMPANY_NAME' in build_tools/build_set_version_info.py  !!!")

    version_str_full, version_tuple = get_version()
    copyright_str = get_copyright_notice(COMPANY_NAME)
    def escape_for_template(s): return s.replace("'", "\\'")
    output_content = VERSION_INFO_TEMPLATE.format(
        FILEVERS_TUPLE=str(version_tuple), PRODVERS_TUPLE=str(version_tuple),
        COMPANY_NAME=escape_for_template(COMPANY_NAME),
        FILE_DESCRIPTION=escape_for_template(FILE_DESCRIPTION),
        VERSION_STR_FULL=version_str_full,
        INTERNAL_NAME=escape_for_template(INTERNAL_NAME),
        COPYRIGHT_STR=escape_for_template(copyright_str),
        ORIGINAL_FILENAME=escape_for_template(ORIGINAL_FILENAME),
        PRODUCT_NAME=escape_for_template(PRODUCT_NAME)
    )
    try:

        with open(VERSION_INFO_OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(output_content)
        print(
            f"[+] Successfully created '{os.path.abspath(VERSION_INFO_OUTPUT_FILE)}' with version {version_str_full}")
    except Exception as e:
        print(
            f"[!] Error writing '{os.path.abspath(VERSION_INFO_OUTPUT_FILE)}': {e}")


if __name__ == "__main__":
    main()
