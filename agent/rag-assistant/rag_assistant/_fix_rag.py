# fix script - clean up web_ui.py
path = 'C:/Users/sm001/WorkBuddy/rag-assistant/rag_assistant/web_ui.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip_until = -1
for i, line in enumerate(lines):
    # Remove return button block
    if '注入回退按钮' in line:
        skip_until = i + 5  # skip ~5 lines of the block
        continue
    if skip_until > i:
        continue
    
    # Remove 知识库概览 card (from <div class="card"> to its closing </div>)
    if '<h2>\U0001f4da 知识库概览</h2>' in line or '<h2>📚 知识库概览</h2>' in line:
        # Walk backwards to find card start
        card_start = len(new_lines) - 1
        while card_start >= 0:
            if '<div class="card">' in new_lines[card_start]:
                break
            card_start -= 1
        if card_start >= 0:
            new_lines = new_lines[:card_start]
            # skip lines until we find 3x </div> closing
            close_count = 0
            for j in range(i, len(lines)):
                if '</div>' in lines[j]:
                    close_count += 1
                    if close_count >= 3:
                        i = j  # continue from here
                        break
            continue
    
    new_lines.append(line)

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f'Processed: {len(lines)} -> {len(new_lines)} lines')
