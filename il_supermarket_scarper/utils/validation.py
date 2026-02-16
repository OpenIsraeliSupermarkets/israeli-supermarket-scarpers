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


def _find_index_safe(array, substring):
    """Return first index containing substring, or None if not found."""
    for i, s in enumerate(array):
        if substring in s:
            return i
    return None


def extract_main_content(text, start_marker="חוקים ותקנות", end_marker="נוסח החוק המעודכן ביותר"):
    """Extract the section between start_marker and end_marker (as string). Return None if not found."""
    lines = text.splitlines()
    start_i = _find_index_safe(lines, start_marker)
    end_i = _find_index_safe(lines, end_marker)
    if start_i is None or end_i is None:
        return None
    return "\n".join(lines[start_i:end_i])


def show_text_diff(text1, text2):
    """show the difference between two text strings in a git-like format"""
    # Split the texts into lines for comparison
    text1_lines = text1.splitlines()
    text2_lines = text2.splitlines()

    start_marker = "חוקים ותקנות"
    end_marker = "נוסח החוק המעודכן ביותר"
    start1 = _find_index_safe(text1_lines, start_marker)
    end1 = _find_index_safe(text1_lines, end_marker)
    start2 = _find_index_safe(text2_lines, start_marker)
    end2 = _find_index_safe(text2_lines, end_marker)

    if start1 is not None and end1 is not None:
        text1_lines = text1_lines[start1:end1]
    if start2 is not None and end2 is not None:
        text2_lines = text2_lines[start2:end2]

    # Use difflib to compare the texts with more context
    diff = difflib.unified_diff(
        text1_lines,
        text2_lines,
        lineterm="",
        fromfile="Expected",
        tofile="Actual",
        n=5,  # Show 5 lines of context around changes
    )

    # Format the output for better readability
    diff_lines = []
    diff_lines.append("\n" + "=" * 80)
    diff_lines.append("DIFF:")
    diff_lines.append("=" * 80)

    for line in diff:
        # Add visual markers for different line types
        if line.startswith("---") or line.startswith("+++"):
            diff_lines.append(line)
        elif line.startswith("-"):
            diff_lines.append(f"- {line[1:]}")  # Removed line
        elif line.startswith("+"):
            diff_lines.append(f"+ {line[1:]}")  # Added line
        elif line.startswith("@@"):
            diff_lines.append("\n" + line)  # Context marker
        else:
            diff_lines.append(f"  {line}")  # Context line

    diff_lines.append("=" * 80)

    return "\n".join(diff_lines)


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
