def compare_hashes(original_map: dict, new_map: dict) -> list:
    """
    Takes original stored JSON hash map and newly generated hash map.
    Detects mismatch and returns the exact page number and line number where tampering occurred.
    Returns a list of mismatches: [{"page": "page_1", "line": "line_2", "type": "modified/missing/added"}, ...]
    """
    mismatches = []
    
    all_pages = set(original_map.keys()).union(set(new_map.keys()))
    
    # Sort pages so we output them in order
    sorted_pages = sorted(list(all_pages), key=lambda x: int(x.split('_')[1]) if '_' in x else 0)
    
    for page in sorted_pages:
        if page not in original_map:
            mismatches.append({"page": page, "line": "all", "type": "added_page"})
            continue
        if page not in new_map:
            mismatches.append({"page": page, "line": "all", "type": "missing_page"})
            continue
            
        orig_lines = original_map[page]
        new_lines = new_map[page]
        
        all_lines = set(orig_lines.keys()).union(set(new_lines.keys()))
        
        # Sort line keys assuming format "line_X"
        sorted_lines = sorted(list(all_lines), key=lambda x: int(x.split('_')[1]) if '_' in x else 0)
        
        for line in sorted_lines:
            if line not in orig_lines:
                mismatches.append({"page": page, "line": line, "type": "added_line"})
            elif line not in new_lines:
                mismatches.append({"page": page, "line": line, "type": "missing_line"})
            elif orig_lines[line] != new_lines[line]:
                mismatches.append({"page": page, "line": line, "type": "modified_line"})
                
    return mismatches
