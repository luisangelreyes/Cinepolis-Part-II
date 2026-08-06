import json

with open("../../cartelera_veracruz_completa.json", "r", encoding="utf-8") as f:
    j = json.load(f)

slugs = sorted(set(func["complejo_slug"] for func in j["funciones"]))
print(f"Complejos con funciones: {len(slugs)}")
for s in slugs:
    count = sum(1 for func in j["funciones"] if func["complejo_slug"] == s)
    print(f"  - {s}: {count} funciones")

print(f"\nTotal funciones: {len(j['funciones'])}")
print(f"Total peliculas: {len(j['peliculas'])}")

# Check which are missing
COMPLEJOS = [
    "cinepolis-la-florida-acayucan",
    "cinepolis-vip-el-dorado-veracruz",
    "cinepolis-las-americas-veracruz",
    "cinepolis-vip-las-americas-veracruz",
    "cinepolis-el-dorado-coatzacoalcos",
    "cinepolis-acaya-coatzacoalcos",
    "cinepolis-plaza-shangri-la-cordoba",
    "cinepolis-plaza-museo-xalapa",
    "cinepolis-plaza-crystal-xalapa",
    "cinepolis-vip-las-americas-xalapa",
    "cinepolis-plaza-las-americas-xalapa",
    "cinepolis-chedraui-martinez-de-la-torre",
    "cinepolis-plaza-minatitlan",
    "cinepolis-plaza-valle-orizaba",
    "cinepolis-rio-blanco-orizaba",
    "cinepolis-plaza-crystal-tuxpan",
    "cinepolis-portal-veracruz",
    "cinepolis-plaza-del-puerto-veracruz",
    "cinepolis-el-dorado-veracruz"
]

missing = [c for c in COMPLEJOS if c not in slugs]
print(f"\nComplejos SIN funciones ({len(missing)}):")
for m in missing:
    print(f"  MISSING: {m}")
