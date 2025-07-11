# config.py

# Default settings for LLM providers (simplified for Python MCP)
DEFAULT_PROVIDERS = [
    {
        "name": "DeepSeek",
        "apiKey": "",
        "baseUrl": "https://api.deepseek.com/v1",
        "model": "deepseek-reasoner",
        "temperature": 0.5
    },
    {
        "name": "OpenAI",
        "apiKey": "",
        "baseUrl": "https://api.openai.com/v1",
        "model": "gpt-4o",
        "temperature": 0.5
    },
    {
        "name": "Anthropic",
        "apiKey": "",
        "baseUrl": "https://api.anthropic.com",
        "model": "claude-3-5-sonnet-20241022",
        "temperature": 0.5
    },
    {
        "name": "Google",
        "apiKey": "",
        "baseUrl": "https://generativelanguage.googleapis.com/v1",
        "model": "gemini-2.0-flash-exp",
        "temperature": 0.5
    },
    {
        "name": "Mistral",
        "apiKey": "",
        "baseUrl": "https://api.mistral.ai/v1",
        "model": "mistral-large-latest",
        "temperature": 0.5
    },
    {
        "name": "Azure OpenAI",
        "apiKey": "",
        "baseUrl": "",
        "model": "gpt-4o",
        "temperature": 0.5,
        "apiVersion": "2025-01-01-preview"
    },
    {
        "name": "LMStudio",
        "apiKey": "EMPTY",
        "baseUrl": "http://localhost:1234/v1",
        "model": "local-model",
        "temperature": 0.7
    },
    {
        "name": "Ollama",
        "apiKey": "",
        "baseUrl": "http://localhost:11434/api",
        "model": "llama3",
        "temperature": 0.7
    },
    {
        "name": "OpenRouter",
        "apiKey": "",
        "baseUrl": "https://openrouter.ai/api/v1",
        "model": "gryphe/mythomax-l2-13b",
        "temperature": 0.7
    }
]

ACTIVE_PROVIDER = "DeepSeek"
CHUNK_WORD_COUNT = 3000
MAX_TOKENS = 8192
ENABLE_DUPLICATE_DETECTION = True

# File Paths
VAULT_ROOT = "E:/convert/undo/feynman"  # Example path, should be configured
CONCEPT_NOTE_FOLDER = "Concepts"
PROCESSED_FILE_FOLDER = "Processed"
CONCEPT_LOG_FOLDER = "Logs/Notemd"
CONCEPT_LOG_FILE_NAME = "Generate.log"

# Search settings
TAVILY_API_KEY = "" # Your Tavily API key
SEARCH_PROVIDER = "tavily" # "tavily" or "duckduckgo"
DDG_MAX_RESULTS = 5
DDG_FETCH_TIMEOUT = 15
MAX_RESEARCH_CONTENT_TOKENS = 3000
ENABLE_RESEARCH_IN_GENERATE_CONTENT = False
TAVILY_MAX_RESULTS = 5
TAVILY_SEARCH_DEPTH = "basic" # "basic" or "advanced"

# Stable API Call Settings
ENABLE_STABLE_API_CALL = False
API_CALL_INTERVAL = 5
API_CALL_MAX_RETRIES = 3

# Multi-model settings (simplified for now, will use active provider)
ADD_LINKS_PROVIDER = "DeepSeek"
RESEARCH_PROVIDER = "DeepSeek"
GENERATE_TITLE_PROVIDER = "DeepSeek"

# Task-specific models (empty means use provider's default)
ADD_LINKS_MODEL = ""
RESEARCH_MODEL = ""
GENERATE_TITLE_MODEL = ""

# Post-processing settings
REMOVE_CODE_FENCES_ON_ADD_LINKS = False

# Language settings
LANGUAGE = "en"
AVAILABLE_LANGUAGES = [
    {"code": "en", "name": "English"},
    {"code": "es", "name": "Español"},
    {"code": "fr", "name": "Français"},
    {"code": "de", "name": "Deutsch"},
    {"code": "it", "name": "Italiano"},
    {"code": "pt", "name": "Português"},
    {"code": "zh-CN", "name": "简体中文"},
    {"code": "ja", "name": "日本語"},
    {"code": "ko", "name": "한국어"},
    {"code": "ru", "name": "Русский"},
    {"code": "ar", "name": "العربية"},
    {"code": "hi", "name": "हिन्दी"},
    {"code": "bn", "name": "বাংলা"},
    {"code": "nl", "name": "Nederlands"},
    {"code": "sv", "name": "Svenska"},
    {"code": "fi", "name": "Suomi"},
    {"code": "da", "name": "Dansk"},
    {"code": "no", "name": "Norsk"},
    {"code": "pl", "name": "Polski"},
    {"code": "tr", "name": "Türkçe"},
    {"code": "he", "name": "עברית"},
    {"code": "th", "name": "ไทย"},
    {"code": "el", "name": "Ελληνικά"},
    {"code": "cs", "name": "Čeština"},
    {"code": "hu", "name": "Magyar"},
    {"code": "ro", "name": "Română"},
    {"code": "uk", "name": "Українська"}
]

# Custom Prompt Settings Defaults
ENABLE_GLOBAL_CUSTOM_PROMPTS = False
CUSTOM_PROMPT_ADD_LINKS = """
Completely decompose and structure the knowledge points in this markdown document, outputting them in markdown format supported by Obsidian. Core knowledge points should be labelled with Obsidian's backlink format [[]]. Do not output anything other than the original text and the requested "Obsidian's backlink format [[]]".

Rules:
1. Only add Obsidian backlinks [[like this]] to core concepts. Do not modify the original text content or formatting otherwise.
2. Skip conventional names (common products, company names, dates, times, individual names) unless they represent a core technical or scientific concept within the text's context.
3. Output the *entire* original content of the chunk, preserving all formatting (headers, lists, code blocks, etc.), with only the added backlinks.
4. Handle duplicate concepts carefully:
    a. If both singular and plural forms of a word/concept appear (e.g., "model" and "models"), only add the backlink to the *first occurrence* of the *singular* form (e.g., [[model]]). Do not link the plural form.
    b. If a single-word concept (e.g., "relaxation") also appears as part of a multi-word concept (e.g., "dielectric relaxation"), only add the backlink to the *multi-word* concept (e.g., [[dielectric relaxation]]). Do not link the standalone single word in this case.
    c. Do not add duplicate backlinks for the exact same concept within this chunk. Link only the first meaningful occurrence.
5. Ignore any "References", "Bibliography", or similar sections, typically found at the end of documents. Do not add backlinks within these sections.
"""
CUSTOM_PROMPT_GENERATE_TITLE = """
Create comprehensive technical documentation about "{TITLE}" with a focus on scientific and mathematical rigor.
{RESEARCH_CONTEXT_SECTION}
Include:
1.  Detailed explanation of core concepts with their mathematical foundations. Start with a Level 2 Header (## {TITLE}).
2.  Key technical specifications with precise values and units (use tables).
3.  Common use cases with quantitative performance metrics.
4.  Implementation considerations with algorithmic complexity analysis (if applicable).
5.  Performance characteristics with statistical measures.
6.  Related technologies with comparative mathematical models. 
7.  Mathematical equations in LaTeX format (using $$...$$ for display and $...$ for inline) with detailed explanations of all parameters and variables. Example: $$ P(f) = \int_{-\infty}^{\infty} p(t) e^{-i2\pi ft} dt $$
8.  Mermaid.js diagram code blocks using the format ```mermaid ... ``` (IMPORTANT: without brackets "()" or "{}" for Mermaid diagrams) for complex relationships or system architectures,Enclosed node names with spaces/special characters in square brackets,which is [ and ], Avoids special LaTeX syntax and Added quotes around subgraph titles with special characters, "subgraph" and "end" cannot appear on the same line!For example:
```mermaid
graph TD
    Start[Input: Year] --> IsDiv400["Year % 400 == 0?"];
    IsDiv400 -- Yes --> Leap[Leap Year, 366 days];
    IsDiv400 -- No --> IsDiv100["Year % 100 == 0?"];
    IsDiv100 -- Yes --> Common1[Common Year, 365 days];
    IsDiv100 -- No --> IsDiv4["Year % 4 == 0?"];
    IsDiv4 -- Yes --> Leap;
    IsDiv4 -- No --> Common2[Common Year, 365 days];
    Leap --> End[End];
    Common1 --> End;
    Common2 --> End;

    style Leap fill:#ccffcc,stroke:#006600
    style Common1 fill:#ffcccc,stroke:#990000
    style Common2 fill:#ffcccc,stroke:#990000
``` and ```mermaid
graph LR
    subgraph "Material Mechanical Properties"
        Stress --> Strain;
        Strain -- "Linear Ratio" --> Youngs_Modulus[E - Young's Modulus<br>Tensile Stiffness];
        Stress -- "Yield Point" --> Yield_Strength[\u03C3y - Yield Strength<br>Onset of Plasticity];
        Stress -- "Maximum Point" --> UTS[UTS - Ultimate Tensile Strength];
        Strain -- "Transverse/Axial Ratio" --> Poissons_Ratio[\u03BD - Poisson's Ratio];
        Shear_Stress --> Shear_Strain;
        Shear_Strain -- "Linear Ratio" --> Shear_Modulus[G - Shear Modulus<br>Shear Stiffness];
        Hydrostatic_Pressure --> Volumetric_Strain;
        Volumetric_Strain -- "Linear Ratio" --> Bulk_Modulus[K - Bulk Modulus<br>Volumetric Stiffness];

        Youngs_Modulus -- "Isotropic Relations" --> Shear_Modulus;
        Youngs_Modulus -- "Isotropic Relations" --> Bulk_Modulus;
        Youngs_Modulus -- "Isotropic Relations" --> Poissons_Ratio;
        Shear_Modulus -- "Isotropic Relations" --> Bulk_Modulus;
        Shear_Modulus -- "Isotropic Relations" --> Poissons_Ratio;
        Bulk_Modulus -- "Isotropic Relations" --> Poissons_Ratio;

        Yield_Strength --> Plasticity[Plastic Deformation Region];
        UTS --> Plasticity;
        Stress_Strain_Curve_Area --> Toughness;

    end

    style Youngs_Modulus fill:#ccf,stroke:#333,stroke-width:2px
    style Shear_Modulus fill:#cfc,stroke:#333,stroke-width:2px
    style Bulk_Modulus fill:#cff,stroke:#333,stroke-width:2px
    style Poissons_Ratio fill:#fcf,stroke:#333,stroke-width:2px
``` and 
```mermaid
graph TD
    WavePattern -->|Mechanical?| Mechanical
    WavePattern -->|Electromagnetic?| Electromagnetic
    Mechanical -->|Longitudinal?| Sound
    Mechanical -->|Transverse?| SeismicWaves
    Sound[Sound Waves] -->|In air?| Acoustic[343 m/s, 20 Hz-20 kHz]
    SeismicWaves[Seismic Waves] -->|Body wave?| PWave[6.5 km/s]
    SeismicWaves -->|Surface wave?| RayleighWave[2.5 km/s]

    Electromagnetic -->|Free space?| EMFreeSpace[c=3e8 m/s]
    Electromagnetic -->|Guided medium?| OpticalFiber[Dispersion=1e-3 ps/nm/km]
``` and ```mermaid
graph TD
    subgraph "Theoretical Frameworks for Electromagnetism"
        QED["Standard Model QED Massless Photon"]
        Proca["Proca Theory Massive Photon - 'Yukawa Photon'"]
        Stueckelberg["Stueckelberg Mechanism Massive Photon"]
        DarkPhoton["Dark Photon Models New Gauge Boson"]
    end

    QED -- "Add Mass Term" --> Proca;
    Proca -- "Breaks Gauge Invariance" --> Issue1["Renormalization/High Energy Issues"];
    QED -- "Introduce Stueckelberg Field" --> Stueckelberg;
    Stueckelberg -- "Preserves Gauge Invariance" --> Proca_Unitary["Unitary Gauge -> Proca"];
    Stueckelberg -- "Theoretically Cleaner" --> Benefit1["Better Renormalizability"];
    QED -- "Add New U1' + Mixing" --> DarkPhoton;

    Proca -- "Feature: Yukawa Potential" --> YP["Vr ~ exp-mr/r"];
    QED -- "Feature: Coulomb Potential" --> CP["Vr ~ 1/r"];
    Proca -- "Feature: 3 d.o.f." --> DOF3["2 Transverse + 1 Longitudinal"];
    QED -- "Feature: 2 d.o.f." --> DOF2["2 Transverse"];

    style QED fill:#ccf,stroke:#333,stroke-width:2px
    style Proca fill:#fcc,stroke:#333,stroke-width:2px
    style Stueckelberg fill:#cfc,stroke:#333,stroke-width:2px
    style DarkPhoton fill:#ffc,stroke:#333,stroke-width:2px
```.
9.  Use bullet points for lists longer than 3 items.
10. Include references to academic papers with DOI where applicable, under a "## References" section.
11. Preserve all mathematical formulas and scientific principles without simplification.
12. Define all variables and parameters used in equations.
13. Include statistical measures and confidence intervals where relevant.

Format directly for Obsidian markdown. Do NOT wrap the entire response in a markdown code block. Start directly with the Level 2 Header.
"""
CUSTOM_PROMPT_RESEARCH_SUMMARIZE = """
Summarize the following search results for the topic "{TOPIC}". Provide a concise yet comprehensive overview. Focus on key findings, data, and important conclusions. Format the summary in Markdown.

Search Results:
{SEARCH_RESULTS_CONTEXT}
"""
