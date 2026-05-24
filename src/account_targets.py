"""Curated account/search universe for the @gpumaxxing growth loop.

The account should orbit AI, compute, energy, robotics, markets, military
technology, accelerationism, and internet-native meme culture. Keep this file
hand-curated: broad enough for network effects, selective enough to preserve
mystique.
"""


TIER1_CORE_AI_FUTURE = [
    "elonmusk",
    "sama",
    "karpathy",
    "lexfridman",
    "DavidSacks",
    "peterthiel",
    "balajis",
    "pmarca",
    "PalmerLuckey",
    "naval",
    "paulg",
]


TIER2_AI_ACCELERATIONISM = [
    "BasedBeffJezos",
    "tsarnick",
    "nearcyan",
    "repligate",
    "roonk",
    "swyx",
    "lilianweng",
    "DrJimFan",
    "ID_AA_Carmack",
    "ylecun",
    "fchollet",
    "AndrewYNg",
    "gwern",
    "jeremyphoward",
    "hardmaru",
    "simonw",
    "mckaywrigley",
    "levelsio",
]


TIER3_DATACENTER_INFRA_ENERGY = [
    "dylan522p",
    "SemiAnalysis_",
    "Jukanlosreve",
    "PatrickMoorhead",
    "IanCutress",
    "anshelsag",
    "ServeTheHome",
    "datacenter",
    "DCDnews",
    "DataCenterDive",
    "CoreWeave",
    "CrusoeEnergy",
    "LambdaAPI",
    "applied_dc",
    "nvidia",
    "AMD",
    "TSMC",
    "ASMLcompany",
    "IREN_Ltd",
    "TeraWulfInc",
    "CipherMining",
    "CleanSpark_Inc",
    "MARAHoldings",
    "RiotPlatforms",
    "Nuc_Eng",
    "EnergyBants",
    "Dr_Keefer",
    "NuclearNY",
    "Oklo",
]


TIER4_SMART_MEMES = [
    "litcapital",
    "gurgavin",
    "unusual_whales",
    "KobeissiLetter",
    "zerohedge",
    "WallStreetSilv",
    "StartupLJackson",
    "VCBrags",
    "BasedBeffJezos",
    "levelsio",
    "mattshumer_",
    "rowancheung",
    "TheRundownAI",
    "AlphaSignalAI",
    "TheAIGRID",
]


TIER5_TECHNO_GEOPOLITICS = [
    "AndurilTech",
    "PalmerLuckey",
    "SpaceX",
    "Starlink",
    "RocketLab",
    "PeterDiamandis",
    "ElbridgeColby",
    "Scholars_Stage",
    "Noahpinion",
    "michaelxpettis",
    "HoansSolo",
    "MacroAlf",
    "DoombergT",
]


MEDIUM_SIZED_DISCOVERY_SEARCHES = [
    "AI agents compute bottleneck min_faves:100",
    "AGI singularity robotics min_faves:100",
    "e/acc AI accelerationism min_faves:50",
    "datacenter power demand AI min_faves:50",
    "hyperscaler capex AI datacenter min_faves:50",
    "nuclear energy datacenter AI min_faves:50",
    "semiconductor GPU supply chain min_faves:50",
    "US China AI race compute min_faves:100",
    "military AI autonomous drones min_faves:50",
    "cyberpunk AI future memes min_faves:50",
    "finance meme AI bubble min_faves:100",
    "techno capitalism AI min_faves:50",
]


GPUMAXXING_SEARCH_QUERIES = [
    "AI agents OR AGI OR singularity lang:en min_faves:300",
    "compute bottleneck OR GPU shortage OR inference economy lang:en min_faves:200",
    "AI datacenter OR power demand OR megawatt lang:en min_faves:200",
    "hyperscaler capex OR AI capex OR datacenter buildout lang:en min_faves:200",
    "nuclear OR grid OR natural gas AI datacenter lang:en min_faves:200",
    "robotics OR humanoid robots OR autonomous systems lang:en min_faves:200",
    "US China AI race OR compute wars OR export controls lang:en min_faves:200",
    "defense AI OR autonomous drones OR military tech lang:en min_faves:150",
    "e/acc OR accelerationism OR techno-capitalism lang:en min_faves:100",
    "cyberpunk OR AI future OR civilization acceleration lang:en min_faves:100",
]


ALL_TARGET_ACCOUNTS = list(dict.fromkeys(
    TIER1_CORE_AI_FUTURE
    + TIER2_AI_ACCELERATIONISM
    + TIER3_DATACENTER_INFRA_ENERGY
    + TIER4_SMART_MEMES
    + TIER5_TECHNO_GEOPOLITICS
))


PRIORITY_REPLY_ACCOUNTS = list(dict.fromkeys(
    TIER1_CORE_AI_FUTURE
    + TIER2_AI_ACCELERATIONISM[:12]
    + TIER3_DATACENTER_INFRA_ENERGY[:18]
    + TIER5_TECHNO_GEOPOLITICS[:8]
))


EARLY_BIRD_ACCOUNTS = list(dict.fromkeys(
    TIER1_CORE_AI_FUTURE
    + TIER2_AI_ACCELERATIONISM
    + TIER3_DATACENTER_INFRA_ENERGY[:22]
    + TIER5_TECHNO_GEOPOLITICS[:10]
))


RETWEET_SOURCE_HANDLES = list(dict.fromkeys(
    TIER1_CORE_AI_FUTURE
    + TIER3_DATACENTER_INFRA_ENERGY
    + TIER5_TECHNO_GEOPOLITICS
    + [
        "Reuters",
        "business",
        "markets",
        "FT",
        "WSJ",
        "CNBC",
        "TechCrunch",
        "TheInformation",
        "verge",
        "WIRED",
        "TheBlock__",
        "CoinDesk",
    ]
))
