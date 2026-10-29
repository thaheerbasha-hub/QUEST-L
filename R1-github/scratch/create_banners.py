import base64
import json

svg_demat = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 240" width="1200" height="240">
  <defs>
    <linearGradient id="bgGradDemat" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#070b14"/>
      <stop offset="55%" stop-color="#0d1526"/>
      <stop offset="100%" stop-color="#041513"/>
    </linearGradient>
    <linearGradient id="btnGradDemat" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#00D09C"/>
      <stop offset="100%" stop-color="#00B887"/>
    </linearGradient>
    <linearGradient id="tagGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="rgba(0, 208, 156, 0.22)"/>
      <stop offset="100%" stop-color="rgba(59, 130, 246, 0.15)"/>
    </linearGradient>
    <radialGradient id="glowDemat" cx="88%" cy="40%" r="50%">
      <stop offset="0%" stop-color="rgba(0, 208, 156, 0.25)"/>
      <stop offset="100%" stop-color="rgba(0, 208, 156, 0)"/>
    </radialGradient>
  </defs>

  <!-- Card Background -->
  <rect width="1200" height="240" rx="14" fill="url(#bgGradDemat)"/>
  <rect width="1200" height="240" rx="14" fill="url(#glowDemat)"/>
  <rect width="1200" height="240" rx="14" fill="none" stroke="rgba(112, 126, 171, 0.26)" stroke-width="1.5"/>

  <!-- Left Accent Stripe -->
  <rect x="0" y="0" width="5" height="240" rx="2" fill="#00D09C"/>

  <!-- Brand Wordmark & Emblem -->
  <g transform="translate(44, 30)">
    <circle cx="20" cy="20" r="20" fill="#00D09C" fill-opacity="0.16" stroke="#00D09C" stroke-width="1.5"/>
    <path d="M12 25 L18 15 L24 21 L29 13" stroke="#00D09C" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    <text x="50" y="28" fill="#ffffff" font-family="'Inter', system-ui, -apple-system, sans-serif" font-size="28" font-weight="900" letter-spacing="-0.5">Groww</text>
  </g>

  <!-- Sponsored Tag -->
  <rect x="180" y="36" width="100" height="24" rx="6" fill="url(#tagGrad)" stroke="rgba(0, 208, 156, 0.35)" stroke-width="1"/>
  <text x="190" y="52" fill="#00D09C" font-family="'Inter', system-ui, sans-serif" font-size="10.5" font-weight="800" letter-spacing="0.8">SPONSORED</text>

  <!-- Headline: Demat Account in 5 mins -->
  <text x="44" y="112" fill="#ffffff" font-family="'Inter', system-ui, -apple-system, sans-serif" font-size="30" font-weight="900" letter-spacing="-0.6">
    Open a Demat Account in 5 mins — Groww
  </text>

  <!-- Subtitle & Value Props -->
  <text x="44" y="152" fill="#cbd5e1" font-family="'Inter', system-ui, -apple-system, sans-serif" font-size="15" font-weight="600">
    ₹0 Account Opening Fee  •  Zero AMC Charges  •  100% Paperless Digital KYC
  </text>

  <!-- Trust Stats -->
  <g transform="translate(44, 192)">
    <text x="0" y="0" fill="#facc15" font-family="'Inter', sans-serif" font-size="13" font-weight="800">★★★★★</text>
    <text x="65" y="-1" fill="#94a3b8" font-family="'Inter', system-ui, sans-serif" font-size="12" font-weight="600">
      4.5+ Rating  •  Trusted by 50M+ Indians  •  SEBI &amp; NSE Registered
    </text>
  </g>

  <!-- Right Side CTA Button -->
  <g transform="translate(860, 84)">
    <rect width="295" height="58" rx="12" fill="url(#btnGradDemat)" filter="drop-shadow(0 6px 16px rgba(0, 208, 156, 0.45))"/>
    <text x="147" y="36" fill="#032117" font-family="'Inter', system-ui, -apple-system, sans-serif" font-size="16" font-weight="900" text-anchor="middle" letter-spacing="0.2">
      Open Free Demat Account →
    </text>
  </g>
  <text x="1007" y="172" fill="#94a3b8" font-family="'Inter', system-ui, sans-serif" font-size="12" font-weight="500" text-anchor="middle">
    Direct Investment • Fast Online Approval
  </text>
</svg>'''

svg_groww = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 240" width="1200" height="240">
  <defs>
    <linearGradient id="bgGradGroww" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0c0f20"/>
      <stop offset="55%" stop-color="#121630"/>
      <stop offset="100%" stop-color="#081822"/>
    </linearGradient>
    <linearGradient id="btnGradGroww" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#00D09C"/>
      <stop offset="100%" stop-color="#38bdf8"/>
    </linearGradient>
    <radialGradient id="glowGroww" cx="88%" cy="40%" r="50%">
      <stop offset="0%" stop-color="rgba(56, 189, 248, 0.22)"/>
      <stop offset="100%" stop-color="rgba(0, 208, 156, 0)"/>
    </radialGradient>
  </defs>

  <!-- Card Background -->
  <rect width="1200" height="240" rx="14" fill="url(#bgGradGroww)"/>
  <rect width="1200" height="240" rx="14" fill="url(#glowGroww)"/>
  <rect width="1200" height="240" rx="14" fill="none" stroke="rgba(112, 126, 171, 0.26)" stroke-width="1.5"/>

  <!-- Left Accent Stripe -->
  <rect x="0" y="0" width="5" height="240" rx="2" fill="#38bdf8"/>

  <!-- Brand Wordmark & Emblem -->
  <g transform="translate(44, 30)">
    <circle cx="20" cy="20" r="20" fill="#38bdf8" fill-opacity="0.16" stroke="#38bdf8" stroke-width="1.5"/>
    <path d="M12 25 L18 15 L24 21 L29 13" stroke="#38bdf8" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    <text x="50" y="28" fill="#ffffff" font-family="'Inter', system-ui, -apple-system, sans-serif" font-size="28" font-weight="900" letter-spacing="-0.5">Groww</text>
  </g>

  <!-- Sponsored Tag -->
  <rect x="180" y="36" width="100" height="24" rx="6" fill="rgba(56, 189, 248, 0.16)" stroke="rgba(56, 189, 248, 0.35)" stroke-width="1"/>
  <text x="190" y="52" fill="#38bdf8" font-family="'Inter', system-ui, sans-serif" font-size="10.5" font-weight="800" letter-spacing="0.8">SPONSORED</text>

  <!-- Headline: Direct Mutual Funds & Indian Equities -->
  <text x="44" y="112" fill="#ffffff" font-family="'Inter', system-ui, -apple-system, sans-serif" font-size="30" font-weight="900" letter-spacing="-0.6">
    Invest in Direct Mutual Funds &amp; Stocks — Groww
  </text>

  <!-- Subtitle & Value Props -->
  <text x="44" y="152" fill="#cbd5e1" font-family="'Inter', system-ui, -apple-system, sans-serif" font-size="15" font-weight="600">
    0% Commission Direct Plans  •  SIP Starting at ₹100  •  Zero Maintenance AMC
  </text>

  <!-- Trust Stats -->
  <g transform="translate(44, 192)">
    <text x="0" y="0" fill="#38bdf8" font-family="'Inter', sans-serif" font-size="12" font-weight="800">⚡ Simple &amp; Fast</text>
    <text x="110" y="-1" fill="#94a3b8" font-family="'Inter', system-ui, sans-serif" font-size="12" font-weight="600">
      India's Leading Investment Platform  •  SEBI Registered Stock Broker
    </text>
  </g>

  <!-- Right Side CTA Button -->
  <g transform="translate(860, 84)">
    <rect width="295" height="58" rx="12" fill="url(#btnGradGroww)" filter="drop-shadow(0 6px 16px rgba(56, 189, 248, 0.45))"/>
    <text x="147" y="36" fill="#031b26" font-family="'Inter', system-ui, -apple-system, sans-serif" font-size="16" font-weight="900" text-anchor="middle" letter-spacing="0.2">
      Start Investing on Groww →
    </text>
  </g>
  <text x="1007" y="172" fill="#94a3b8" font-family="'Inter', system-ui, sans-serif" font-size="12" font-weight="500" text-anchor="middle">
    Direct Mutual Funds • Equities • ETFs
  </text>
</svg>'''

svg_phonepe = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 240" width="1200" height="240">
  <defs>
    <linearGradient id="bgGradPhonePe" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0b0716"/>
      <stop offset="55%" stop-color="#160e29"/>
      <stop offset="100%" stop-color="#241240"/>
    </linearGradient>
    <linearGradient id="btnGradPhonePe" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#8b5cf6"/>
      <stop offset="100%" stop-color="#6739b7"/>
    </linearGradient>
    <radialGradient id="glowPhonePe" cx="88%" cy="40%" r="50%">
      <stop offset="0%" stop-color="rgba(139, 92, 246, 0.3)"/>
      <stop offset="100%" stop-color="rgba(95, 37, 159, 0)"/>
    </radialGradient>
  </defs>

  <!-- Card Background -->
  <rect width="1200" height="240" rx="14" fill="url(#bgGradPhonePe)"/>
  <rect width="1200" height="240" rx="14" fill="url(#glowPhonePe)"/>
  <rect width="1200" height="240" rx="14" fill="none" stroke="rgba(139, 92, 246, 0.35)" stroke-width="1.5"/>

  <!-- Left Accent Stripe -->
  <rect x="0" y="0" width="5" height="240" rx="2" fill="#8b5cf6"/>

  <!-- Brand Wordmark & Emblem -->
  <g transform="translate(44, 30)">
    <circle cx="20" cy="20" r="20" fill="#5f259f" stroke="#8b5cf6" stroke-width="1.5"/>
    <text x="20" y="27" fill="#ffffff" font-family="'Inter', sans-serif" font-size="20" font-weight="900" text-anchor="middle">पे</text>
    <text x="50" y="28" fill="#ffffff" font-family="'Inter', system-ui, -apple-system, sans-serif" font-size="28" font-weight="900" letter-spacing="-0.5">PhonePe</text>
    <text x="175" y="28" fill="#c084fc" font-family="'Inter', system-ui, sans-serif" font-size="22" font-weight="700">| Share.Market</text>
  </g>

  <!-- Sponsored Tag -->
  <rect x="360" y="36" width="100" height="24" rx="6" fill="rgba(139, 92, 246, 0.2)" stroke="rgba(192, 132, 252, 0.4)" stroke-width="1"/>
  <text x="370" y="52" fill="#c084fc" font-family="'Inter', system-ui, sans-serif" font-size="10.5" font-weight="800" letter-spacing="0.8">SPONSORED</text>

  <!-- Headline: Trade Stocks & ETFs with Share.Market -->
  <text x="44" y="112" fill="#ffffff" font-family="'Inter', system-ui, -apple-system, sans-serif" font-size="30" font-weight="900" letter-spacing="-0.6">
    Trade Stocks &amp; Wealth Baskets — Share.Market by PhonePe
  </text>

  <!-- Subtitle & Value Props -->
  <text x="44" y="152" fill="#cbd5e1" font-family="'Inter', system-ui, -apple-system, sans-serif" font-size="15" font-weight="600">
    Zero Account Opening Fee  •  Intelligence-Led Stock Baskets  •  Backed by 500M+ Indians
  </text>

  <!-- Trust Stats -->
  <g transform="translate(44, 192)">
    <text x="0" y="0" fill="#facc15" font-family="'Inter', sans-serif" font-size="12" font-weight="800">🛡️ Trusted Ecosystem</text>
    <text x="145" y="-1" fill="#94a3b8" font-family="'Inter', system-ui, sans-serif" font-size="12" font-weight="600">
      SEBI Registered Stock Broker  •  Fast UPI Onboarding in Minutes
    </text>
  </g>

  <!-- Right Side CTA Button -->
  <g transform="translate(860, 84)">
    <rect width="295" height="58" rx="12" fill="url(#btnGradPhonePe)" filter="drop-shadow(0 6px 16px rgba(103, 57, 183, 0.5))"/>
    <text x="147" y="36" fill="#ffffff" font-family="'Inter', system-ui, -apple-system, sans-serif" font-size="16" font-weight="900" text-anchor="middle" letter-spacing="0.2">
      Open Account on PhonePe →
    </text>
  </g>
  <text x="1007" y="172" fill="#a78bfa" font-family="'Inter', system-ui, sans-serif" font-size="12" font-weight="500" text-anchor="middle">
    Stocks • Wealth Baskets • F&amp;O
  </text>
</svg>'''

b64_demat = 'data:image/svg+xml;base64,' + base64.b64encode(svg_demat.encode('utf-8')).decode('ascii')
b64_groww = 'data:image/svg+xml;base64,' + base64.b64encode(svg_groww.encode('utf-8')).decode('ascii')
b64_phonepe = 'data:image/svg+xml;base64,' + base64.b64encode(svg_phonepe.encode('utf-8')).decode('ascii')

config = {
    "_note": "IMPORTANT: These click_url values must be swapped for actual affiliate/referral links once a real partnership is set up with each platform (Groww referral program, PhonePe partner program, etc.) — a plain link to their homepage generates no revenue on its own.",
    "dashboard_top": {
        "image_url": b64_demat,
        "click_url": "https://groww.in/open-demat-account",
        "alt": "Sponsored — Open a Demat Account"
    },
    "module_hub_top": {
        "image_url": b64_groww,
        "click_url": "https://groww.in/",
        "alt": "Sponsored — Groww"
    },
    "module_hub_phonepe": {
        "image_url": b64_phonepe,
        "click_url": "https://share.market/",
        "alt": "Sponsored — Share.Market by PhonePe"
    }
}

with open("quest_app/ad_banners.json", "w", encoding="utf-8") as f:
    json.dump(config, f, indent=2, ensure_ascii=False)

print("Created quest_app/ad_banners.json with Groww Demat, Groww platform, and PhonePe Share.Market creatives!")

