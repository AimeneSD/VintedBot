import os

filepath = "utils/vinted.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# We need to extract the download_image block
start_idx = content.find("async def download_image")
end_idx = len(content)

download_block = content[start_idx:end_idx]

# Clean up the end of the class
class_end_idx = content.find("vinted_client = VintedClient()")

# The original block is mangled, let's just replace it entirely.
clean_content = content[:class_end_idx].strip()

download_func = """
    async def download_image(self, url: str) -> bytes:
        \"\"\"Télécharge une image en RAM\"\"\"
        await self._init_session()
        if not self.cookie_valid:
            return b""
            
        try:
            async with self.session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.read()
        except Exception as e:
            print(f"[VintedClient] Erreur telechargement image: {e}")
        return b""

vinted_client = VintedClient()
"""

new_content = clean_content + "\n" + download_func
with open(filepath, "w", encoding="utf-8") as f:
    f.write(new_content)
print("File fixed!")
