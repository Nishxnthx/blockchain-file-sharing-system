import difflib

def generate_diff_html(original_lines_list: list, new_lines_list: list) -> str:
    """
    Highlights the modified text.
    Generates an HTML output showing original vs modified lines using python's difflib.
    """
    differ = difflib.HtmlDiff(wrapcolumn=80)
    html_out = differ.make_file(original_lines_list, new_lines_list, 
                                fromdesc="Original Report", todesc="Tampered Report",
                                context=False) # Context=False shows whole file, or Context=True shows just differences
    return html_out
