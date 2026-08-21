# Project Context

- The project is a Vinted Sniper Discord bot using a proxy to bypass Cloudflare.
- Uses Gemini 2.5 Flash for semantic matching and condition estimation.
- Uses a dual-filter AI approach: first text, then image (if text passes).
- Fully refactored into a Discord Cogs architecture.
- Uses remote MySQL database (Alwaysdata) for persistence on cloud hosts like Render.

- Implemented Gemini Model Rotation to pool free API tier limits (up to 65 RPM).
- Injected estimated total price (Item + Protection + Shipping) into AI logic and Discord Embed.
- Added 1-Click Fast Checkout link on Discord to bypass Vinted item page.
- Modified Sniper instructions to accept "too good to be true" prices unconditionally.