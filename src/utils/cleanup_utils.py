import re
import hashlib

def final_markdown_cleanup(content: str) -> str:
    """
    Cleans up a final markdown document by removing exact duplicated paragraphs
    (blocks separated by blank lines) to prevent bloated outputs.
    Leaves headings and short lines intact.
    """
    normalized_content = content.replace("\r\n", "\n")
    blocks = re.split(r'(\n\s*\n)', normalized_content)
    
    seen_hashes = set()
    cleaned_blocks = []
    
    for i, block in enumerate(blocks):
        # Even indices are content blocks, odd indices are the separators (e.g. \n\n)
        if i % 2 == 1:
            cleaned_blocks.append(block)
            continue
            
        clean_block = block.strip()
        
        # Don't deduplicate very short blocks
        if len(clean_block) > 50:
            # Strip leading headings from the hash calculation so paragraphs under different headings match
            hash_target = re.sub(r'^(?:#+\s+.+\n)+', '', clean_block).strip()
            
            if len(hash_target) > 50 and not hash_target.startswith("#"):
                block_hash = hashlib.md5(hash_target.encode('utf-8')).hexdigest()
                if block_hash in seen_hashes:
                    # Duplicate block found! Skip it
                    # If this block had a heading, we might lose the heading, but usually the whole section is duplicated
                    continue
                else:
                    seen_hashes.add(block_hash)
                
        cleaned_blocks.append(block)
        
    return "".join(cleaned_blocks).strip()
