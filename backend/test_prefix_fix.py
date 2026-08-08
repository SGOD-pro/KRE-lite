from thefuzz import fuzz

q_words = ['for', 'the', 'base', 'models', 'we', 'used', 'a', 'single', 'model', 'obtained', 'by', 'averaging', 'the', 'last', '5', 'che']
window = ['for', 'the', 'base', 'models', 'we', 'used', 'a', 'single', 'model', 'obtained', 'by', 'averaging', 'the', 'last', '5', 'checkpoints']

STOPWORDS = {"a", "an", "the", "and", "or", "but", "if", "for", "with", "by", "we", "used"}

print("--- BEFORE FIX ---")
has_fake_entity = False
for qw in q_words:
    if qw not in STOPWORDS and len(qw) > 2:
        if not any(fuzz.ratio(qw, tw) >= 80 for tw in window):
            print(f"Failed on: {qw} vs window")
            has_fake_entity = True
            break
print(f"has_fake_entity: {has_fake_entity}")

print("\n--- AFTER FIX ---")
has_fake_entity_fixed = False
for qw in q_words:
    if qw not in STOPWORDS and len(qw) > 2:
        if not any(fuzz.ratio(qw, tw) >= 80 or (len(qw) >= 3 and tw.startswith(qw)) or (len(tw) >= 3 and qw.startswith(tw)) for tw in window):
            print(f"Failed on: {qw} vs window")
            has_fake_entity_fixed = True
            break
print(f"has_fake_entity_fixed: {has_fake_entity_fixed}")
