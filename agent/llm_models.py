import os
import sys
import getpass
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env if present (optional file)
load_dotenv()


def set_temporary_api_key(key: str, provider: str = "groq"):
    """
    Set API key in os.environ temporarily in memory without saving to disk / .env.
    Refreshes groq_llm and google_llm references.
    """
    global groq_llm, google_llm, default_llm
    key = str(key).strip().strip('"').strip("'")
    if not key:
        return

    # Auto-detect provider if starts with standard prefix
    if key.startswith("gsk_") or provider.lower() == "groq":
        os.environ["GROQ_API_KEY"] = key
        os.environ.pop("GOOGLE_API_KEY", None)
        os.environ.pop("GEMINI_API_KEY", None)
    elif key.startswith("AIza") or provider.lower() in ("gemini", "google"):
        os.environ["GOOGLE_API_KEY"] = key
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ.pop("GROQ_API_KEY", None)
    else:
        if provider.lower() in ("gemini", "google"):
            os.environ["GOOGLE_API_KEY"] = key
            os.environ.pop("GEMINI_API_KEY", None)
            os.environ.pop("GROQ_API_KEY", None)
        else:
            os.environ["GROQ_API_KEY"] = key
            os.environ.pop("GOOGLE_API_KEY", None)
            os.environ.pop("GEMINI_API_KEY", None)

    _init_models()


def prompt_user_for_api_key():
    """
    Prompts the user interactively in the terminal for either a Groq or Gemini API key
    if none is present in os.environ.
    Stores the key temporarily in os.environ in memory only (never written to disk).
    """
    groq_key = os.getenv("GROQ_API_KEY")
    google_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

    if not groq_key and not google_key:
        if sys.stdin and sys.stdin.isatty():
            print("\n" + "=" * 55)
            print("🔑 RetailPilot: Temporary LLM API Key Setup")
            print("No API key found in current environment.")
            print("You only need ONE key: Groq OR Gemini (not all keys required).")
            print("This key is stored temporarily in memory (os.environ).")
            print("=" * 55)
            try:
                choice = input("Select provider ([1] Groq (default) / [2] Gemini): ").strip()
                if choice == "2":
                    key = getpass.getpass("Enter your Gemini API key (hidden): ").strip()
                    if key:
                        set_temporary_api_key(key, provider="gemini")
                        print("✅ Gemini API key temporarily loaded into memory (os.environ).\n")
                else:
                    key = getpass.getpass("Enter your Groq API key (hidden): ").strip()
                    if key:
                        set_temporary_api_key(key, provider="groq")
                        print("✅ Groq API key temporarily loaded into memory (os.environ).\n")
            except (EOFError, KeyboardInterrupt):
                pass


groq_llm = None
google_llm = None
default_llm = None


def _init_models():
    global groq_llm, google_llm, default_llm
    groq_key = os.getenv("GROQ_API_KEY")
    google_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

    if groq_key:
        try:
            from langchain_groq import ChatGroq
            groq_llm = ChatGroq(model="openai/gpt-oss-120b")
        except Exception as e:
            logger.warning(f"Could not initialize Groq LLM: {e}")
            groq_llm = None
    else:
        groq_llm = None

    if google_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            google_llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                temperature=0.3
            )
        except Exception as e:
            logger.warning(f"Could not initialize Google Gemini LLM: {e}")
            google_llm = None
    else:
        google_llm = None

    default_llm = groq_llm or google_llm


def get_active_llm():
    """Return the active configured LLM (Groq or Gemini)."""
    global default_llm, groq_llm, google_llm
    if default_llm is None:
        _init_models()
    if default_llm is None:
        prompt_user_for_api_key()
        _init_models()
    if default_llm is None:
        raise ValueError(
            "No LLM API key configured. Please set GROQ_API_KEY or GOOGLE_API_KEY in os.environ "
            "(e.g. export GROQ_API_KEY='your_key' or use set_temporary_api_key())."
        )
    return default_llm


# Interactive check and initial model load
prompt_user_for_api_key()
_init_models()