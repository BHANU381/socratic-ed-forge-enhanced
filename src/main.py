import json
import os
import time
import datetime
from dotenv import load_dotenv
from src.agents import ContentGenerator, Critic, Editor, Librarian

# Load environment variables
load_dotenv()

# Define Project Root relative to this file's location
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def log_event(role, message):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    clean_message = message.encode('ascii', 'ignore').decode('ascii')
    log_entry = f"[{ts}] **{role}**: {clean_message}\n"
    # Fixed: Use absolute path to the root data folder
    log_dir = os.path.join(PROJECT_ROOT, 'data')
    os.makedirs(log_dir, exist_ok=True)
    with open(os.path.join(log_dir, 'logs.txt'), 'a', encoding='utf-8') as f:
        f.write(log_entry)

def update_status(message):
    clean_message = message.encode('ascii', 'ignore').decode('ascii')
    # Fixed: Use absolute path to the root data folder
    status_dir = os.path.join(PROJECT_ROOT, 'data')
    os.makedirs(status_dir, exist_ok=True)
    with open(os.path.join(status_dir, 'status.txt'), 'w', encoding='utf-8') as f:
        f.write(clean_message)

def main():
    # Fixed: All paths are now absolute relative to PROJECT_ROOT
    input_path = os.path.join(PROJECT_ROOT, 'data', 'input', 'course_input.json')
    output_dir = os.path.join(PROJECT_ROOT, 'data', 'output')
    log_path = os.path.join(PROJECT_ROOT, 'data', 'logs.txt')
    
    if not os.path.exists(input_path):
        print(f"ERROR: Input file not found at {input_path}")
        return

    with open(input_path, 'r') as f:
        data = json.load(f)
    
    safe_course_name = "".join([c if c.isalnum() else "_" for c in data['course_name']])
    master_file = os.path.join(output_dir, f"{safe_course_name}.md")
    
    os.makedirs(output_dir, exist_ok=True)
    if os.path.exists(log_path): os.remove(log_path)

    # Initialize Agents
    generator = ContentGenerator("Content Generator")
    critic = Critic("Critic")
    editor = Editor("Editor")
    librarian = Librarian("Librarian")

    # 1. Start Book
    with open(master_file, 'w', encoding='utf-8') as f:
        f.write(f"# {data['course_name']}\n\n")
        f.write(f"**Topic:** {data['topic']}\n\n")
        f.write("# Table of Contents\n\n")
        for i, mod in enumerate(data['modules']):
            f.write(f"{i+1}. {mod['title']}\n")
            for sub in mod.get('submodules', []):
                f.write(f"   - {sub}\n")
        f.write("\n---\n\n")
    
    log_event("System", "Starting generation pipeline (Class-Based Agents)...")

    # 2. Module & Submodule Generation Loop
    for i, mod in enumerate(data['modules']):
        with open(master_file, 'a', encoding='utf-8') as f:
            f.write(f"\n# Module {i+1}: {mod['title']}\n\n")
        
        for sub in mod.get('submodules', []):
            update_status(f"Preparing {sub}...")
            time.sleep(5) 
            
            update_status(f"Generator Agent: Drafting '{sub}'")
            log_event("Generator", f"Drafting submodule: {sub}")
            
            try:
                draft = generator.generate(mod['title'], sub)
            except Exception as e:
                log_event("Error", f"Drafting failed: {e}")
                update_status(f"Error: {e}. Retrying...")
                time.sleep(30)
                continue
            
            # --- THE REFLECTIVE LOOP ---
            approved = False
            iterations = 0
            max_iterations = 3
            
            while not approved and iterations < max_iterations:
                iterations += 1
                update_status(f"Critic Agent: Reviewing '{sub}' (Attempt {iterations})")
                log_event("Critic", f"Reviewing {sub} (Attempt {iterations})")
                
                try:
                    feedback = critic.critique(draft)
                    
                    if "APPROVED" in feedback.upper():
                        approved = True
                        update_status(f"Approved: {sub}")
                        log_event("Critic", f"Approved: {sub}")
                    else:
                        update_status(f"Editor Agent: Refining '{sub}'")
                        log_event("Editor", f"Refining {sub} based on feedback.")
                        draft = editor.edit(draft, feedback)
                        time.sleep(10)
                except Exception as e:
                    log_event("Error", f"Agent error: {e}")
                    update_status(f"Agent Error: {e}. Waiting...")
                    time.sleep(30)
            
            with open(master_file, 'a', encoding='utf-8') as f:
                f.write(f"\n## Submodule: {sub}\n\n{draft}\n\n")
            
            time.sleep(10) 
            
    # 3. THE LIBRARIAN PASS (Final Structural Audit)
    update_status("Librarian Agent: Performing final structural audit...")
    log_event("Librarian", "Starting final structural audit of complete book.")
    
    with open(master_file, 'r', encoding='utf-8') as f:
        full_book = f.read()
    
    try:
        structure_feedback = librarian.audit_structure(full_book)
        if "APPROVED" not in structure_feedback.upper():
            log_event("Librarian", "Structural issues found. Appending audit log.")
            with open(master_file, 'a', encoding='utf-8') as f:
                f.write(f"\n\n---\n\n### Structural Audit Log\n{structure_feedback}\n")
        else:
            log_event("Librarian", "Structure perfection confirmed.")
            update_status("Librarian: Structure Approved.")
    except Exception as e:
        log_event("Error", f"Librarian error: {e}")
        update_status(f"Librarian Error: {e}")

    update_status("Generation Complete! Book Created.")
    log_event("System", "Course generation pipeline finished successfully.")

if __name__ == "__main__":
    main()
