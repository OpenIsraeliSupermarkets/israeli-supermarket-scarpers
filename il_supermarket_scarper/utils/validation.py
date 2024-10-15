import re
import difflib


def is_valid_chain_name(input_string):
    """check the chain name is in a valid folder foramt"""
    # Regular expression pattern to match only letters (a-z, case insensitive) and hyphens (-)
    pattern = r"^[a-zA-Z0-9-]+$"

    # Use re.match to check if the entire string matches the pattern
    return bool(re.match(pattern, input_string))


def find_index_with_substring(array, substring):
    """Find the index of the first element in the array that contains the substring"""
    return [i for i, s in enumerate(array) if substring in s][0]


def show_text_diff(text1, text2):
    """show the difference between two text strings"""
    # Split the texts into lines for comparison
    text1_lines = text1.splitlines()
    text2_lines = text2.splitlines()

    text1_lines = text1_lines[
        find_index_with_substring(
            text1_lines, "חוקים ותקנות"
        ) : find_index_with_substring(text1_lines, "נוסח החוק המעודכן ביותר")
    ]
    text2_lines = text2_lines[
        find_index_with_substring(
            text2_lines, "חוקים ותקנות"
        ) : find_index_with_substring(text2_lines, "נוסח החוק המעודכן ביותר")
    ]

    # Use difflib to compare the texts
    diff = difflib.unified_diff(
        text1_lines, text2_lines, lineterm="", fromfile="Text1", tofile="Text2"
    )

    # Join the diff output and return
    return "\n".join(diff)


def change_xml_encoding(file_path):
    """change the encoding if failing with utf-8"""
    with open(file_path, "rb") as file:  # pylint: disable=unspecified-encoding
        # Read the XML file content
        content = file.read()

    content = content.decode("ISO-8859-8", errors="replace")

    # Save the file with the new encoding declaration
    with open(file_path, "wb") as file:
        file.write(
            content.replace('encoding="ISO-8859-8"', 'encoding="UTF-8"').encode("utf-8")
        )
