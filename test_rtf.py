from striprtf.striprtf import rtf_to_text
with open('test_real_mes/b_g/plan/Ведомость координат_aLnZAW.rtf', 'r', encoding='cp1251', errors='ignore') as f:
    rtf = f.read()
text = rtf_to_text(rtf)
print(text[:2000])  # Первые 2000 символов