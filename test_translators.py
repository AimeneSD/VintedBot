from deep_translator import GoogleTranslator, MyMemoryTranslator, LingueeTranslator, PonsTranslator
text = "Funziona"

print("Google:", GoogleTranslator(source='auto', target='fr').translate(text))
try:
    print("MyMemory:", MyMemoryTranslator(source='it', target='fr').translate(text))
except Exception as e: print("MyMemory error:", e)

