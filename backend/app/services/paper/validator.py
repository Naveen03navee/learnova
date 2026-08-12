from app.models.paper import QuestionPaper

def validate_structural_integrity(paper: QuestionPaper) -> list[str]:
    errors = []
    
    blueprint = paper.config
    sections_blueprint = blueprint.get("sections", [])
    
    # Group items by section
    items_by_section = {}
    for item in paper.items:
        if item.section_name not in items_by_section:
            items_by_section[item.section_name] = []
        items_by_section[item.section_name].append(item)
        
    for sec_config in sections_blueprint:
        sec_name = sec_config["name"]
        expected_count = sec_config["count"]
        expected_type = sec_config["question_type"].upper()
        expected_marks_per_q = sec_config["marks_per_question"]
        
        items = items_by_section.get(sec_name, [])
        
        # Validate count
        if len(items) != expected_count:
            errors.append(f"Section '{sec_name}' expects {expected_count} questions, found {len(items)}.")
            
        # Validate items
        for idx, item in enumerate(items):
            q_num = idx + 1
            
            # Validate marks
            marks = item.marks_override if item.marks_override is not None else item.marks_snapshot
            if marks != expected_marks_per_q:
                errors.append(f"Section '{sec_name}' Question {q_num}: expected {expected_marks_per_q} marks, found {marks}.")
                
            # Validate Content
            content = item.content_snapshot
            
            if not content:
                errors.append(f"Section '{sec_name}' Question {q_num}: missing content snapshot.")
                continue
                
            if "correct_answer" not in content or not content["correct_answer"]:
                errors.append(f"Section '{sec_name}' Question {q_num}: missing correct_answer.")
                
            if expected_type == "MCQ":
                options = content.get("options", [])
                if not options or len(options) < 2:
                    errors.append(f"Section '{sec_name}' Question {q_num}: MCQ requires at least 2 options.")
                
                if "correct_answer" in content:
                    valid_ans = False
                    ca = str(content["correct_answer"]).lower().strip()
                    for opt in options:
                        if ca == str(opt.get("id", "")).lower().strip() or ca == str(opt.get("text", "")).lower().strip():
                            valid_ans = True
                            break
                    if not valid_ans:
                        errors.append(f"Section '{sec_name}' Question {q_num}: correct_answer '{content['correct_answer']}' does not match any option.")
    
    # Check for sections in items that are not in blueprint
    blueprint_section_names = {s["name"] for s in sections_blueprint}
    for sec_name in items_by_section.keys():
        if sec_name not in blueprint_section_names:
            errors.append(f"Found orphaned section '{sec_name}' not present in blueprint.")
            
    return errors
