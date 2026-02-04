"""
Module d'internationalisation (i18n) pour pecunia-desktop.

Ce module gère:
- Chargement des fichiers de traduction JSON
- Détection automatique de la langue système
- Fonction tr() pour les traductions
- Fallback vers le français par défaut
"""

import json
import locale
import os
from pathlib import Path
from typing import Any, Dict, Optional
from functools import lru_cache

# Chemin vers les fichiers de traduction
TRANSLATIONS_DIR = Path(__file__).parent / "translations"

# Langues supportées
SUPPORTED_LANGUAGES = {
    "fr": "Français",
    "en": "English",
}

# Langue par défaut (fallback)
DEFAULT_LANGUAGE = "fr"

# Cache des traductions chargées
_translations_cache: Dict[str, Dict[str, Any]] = {}

# Langue courante
_current_language: str = DEFAULT_LANGUAGE


def get_system_language() -> str:
    """
    Détecte la langue du système d'exploitation.

    Returns:
        Code de langue (fr, en) ou langue par défaut si non supportée.
    """
    try:
        # Récupérer la locale système
        system_locale = locale.getdefaultlocale()[0]

        if system_locale:
            # Extraire le code de langue (ex: fr_FR -> fr)
            lang_code = system_locale.split("_")[0].lower()

            # Vérifier si la langue est supportée
            if lang_code in SUPPORTED_LANGUAGES:
                return lang_code

        # Fallback: essayer avec getlocale
        try:
            system_locale = locale.getlocale()[0]
            if system_locale:
                lang_code = system_locale.split("_")[0].lower()
                if lang_code in SUPPORTED_LANGUAGES:
                    return lang_code
        except Exception:
            pass

    except Exception:
        pass

    return DEFAULT_LANGUAGE


def load_translations(language: str) -> Dict[str, Any]:
    """
    Charge les traductions depuis un fichier JSON.

    Args:
        language: Code de langue (fr, en)

    Returns:
        Dictionnaire des traductions
    """
    global _translations_cache

    # Vérifier le cache
    if language in _translations_cache:
        return _translations_cache[language]

    # Chemin du fichier de traduction
    translation_file = TRANSLATIONS_DIR / f"{language}.json"

    if not translation_file.exists():
        # Si le fichier n'existe pas, essayer la langue par défaut
        if language != DEFAULT_LANGUAGE:
            return load_translations(DEFAULT_LANGUAGE)
        return {}

    try:
        with open(translation_file, "r", encoding="utf-8") as f:
            translations = json.load(f)
            _translations_cache[language] = translations
            return translations
    except (json.JSONDecodeError, IOError) as e:
        print(f"Erreur lors du chargement des traductions ({language}): {e}")
        if language != DEFAULT_LANGUAGE:
            return load_translations(DEFAULT_LANGUAGE)
        return {}


def set_language(language: str) -> bool:
    """
    Définit la langue courante de l'application.

    Args:
        language: Code de langue (fr, en)

    Returns:
        True si la langue a été changée, False sinon
    """
    global _current_language

    if language not in SUPPORTED_LANGUAGES:
        print(f"Langue non supportée: {language}")
        return False

    _current_language = language
    # Précharger les traductions
    load_translations(language)
    return True


def get_language() -> str:
    """
    Retourne la langue courante.

    Returns:
        Code de langue courant
    """
    return _current_language


def get_available_languages() -> Dict[str, str]:
    """
    Retourne les langues disponibles.

    Returns:
        Dictionnaire {code: nom} des langues disponibles
    """
    return SUPPORTED_LANGUAGES.copy()


def _get_nested_value(data: Dict[str, Any], key: str) -> Optional[str]:
    """
    Récupère une valeur imbriquée dans un dictionnaire.

    Args:
        data: Dictionnaire de données
        key: Clé avec notation pointée (ex: "menu.file.open")

    Returns:
        Valeur trouvée ou None
    """
    keys = key.split(".")
    current = data

    for k in keys:
        if isinstance(current, dict) and k in current:
            current = current[k]
        else:
            return None

    return current if isinstance(current, str) else None


def tr(key: str, default: Optional[str] = None, **kwargs) -> str:
    """
    Fonction principale de traduction.

    Supporte:
    - Clés imbriquées avec notation pointée (ex: "menu.file.open")
    - Paramètres de substitution (ex: tr("welcome", name="John"))
    - Valeur par défaut si la clé n'existe pas

    Args:
        key: Clé de traduction
        default: Valeur par défaut si la traduction n'existe pas
        **kwargs: Paramètres de substitution

    Returns:
        Texte traduit

    Exemples:
        tr("menu.file")
        tr("welcome_message", name="Jean")
        tr("unknown_key", default="Texte par défaut")
    """
    # Charger les traductions pour la langue courante
    translations = load_translations(_current_language)

    # Chercher la traduction
    value = _get_nested_value(translations, key)

    # Si non trouvé, essayer la langue par défaut
    if value is None and _current_language != DEFAULT_LANGUAGE:
        default_translations = load_translations(DEFAULT_LANGUAGE)
        value = _get_nested_value(default_translations, key)

    # Si toujours non trouvé, utiliser la valeur par défaut ou la clé
    if value is None:
        value = default if default is not None else key

    # Substitution des paramètres
    if kwargs:
        try:
            value = value.format(**kwargs)
        except KeyError as e:
            print(f"Paramètre manquant dans la traduction '{key}': {e}")

    return value


def tr_plural(key: str, count: int, **kwargs) -> str:
    """
    Traduction avec gestion du pluriel.

    La clé doit avoir des sous-clés 'zero', 'one', 'other'.

    Args:
        key: Clé de traduction de base
        count: Nombre pour déterminer la forme
        **kwargs: Paramètres de substitution

    Returns:
        Texte traduit avec la forme correcte

    Exemple:
        tr_plural("items_count", 5, count=5)
        # Utilise "items_count.other" avec count=5
    """
    # Déterminer la forme plurielle
    if count == 0:
        plural_key = f"{key}.zero"
    elif count == 1:
        plural_key = f"{key}.one"
    else:
        plural_key = f"{key}.other"

    # Ajouter count aux kwargs s'il n'y est pas
    if "count" not in kwargs:
        kwargs["count"] = count

    # Essayer la forme spécifique, sinon la forme générale
    result = tr(plural_key, default=None, **kwargs)
    if result == plural_key:
        result = tr(f"{key}.other", default=key, **kwargs)

    return result


def format_currency(amount: float, currency: str = "EUR") -> str:
    """
    Formate un montant selon la locale courante.

    Args:
        amount: Montant à formater
        currency: Code de devise (EUR, USD, etc.)

    Returns:
        Montant formaté
    """
    symbols = {
        "EUR": "€",
        "USD": "$",
        "GBP": "£",
        "CHF": "CHF",
        "CAD": "$ CA",
    }

    symbol = symbols.get(currency, currency)

    # Format selon la langue
    if _current_language == "fr":
        # Format français: 1 234,56 €
        formatted = f"{amount:,.2f}".replace(",", " ").replace(".", ",")
        return f"{formatted} {symbol}"
    else:
        # Format anglais: €1,234.56
        formatted = f"{amount:,.2f}"
        return f"{symbol}{formatted}"


def format_date(date_str: str, format_type: str = "short") -> str:
    """
    Formate une date selon la locale courante.

    Args:
        date_str: Date au format ISO (YYYY-MM-DD)
        format_type: Type de format ('short', 'long', 'full')

    Returns:
        Date formatée
    """
    from datetime import datetime

    try:
        date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        return date_str

    months_fr = [
        "", "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre"
    ]

    months_en = [
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]

    if _current_language == "fr":
        if format_type == "short":
            return date.strftime("%d/%m/%Y")
        elif format_type == "long":
            return f"{date.day} {months_fr[date.month]} {date.year}"
        else:  # full
            days = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
            return f"{days[date.weekday()]} {date.day} {months_fr[date.month]} {date.year}"
    else:
        if format_type == "short":
            return date.strftime("%m/%d/%Y")
        elif format_type == "long":
            return f"{months_en[date.month]} {date.day}, {date.year}"
        else:  # full
            return date.strftime("%A, %B %d, %Y")


def format_number(number: float, decimals: int = 2) -> str:
    """
    Formate un nombre selon la locale courante.

    Args:
        number: Nombre à formater
        decimals: Nombre de décimales

    Returns:
        Nombre formaté
    """
    if _current_language == "fr":
        formatted = f"{number:,.{decimals}f}".replace(",", " ").replace(".", ",")
    else:
        formatted = f"{number:,.{decimals}f}"

    return formatted


def format_percentage(value: float, decimals: int = 1) -> str:
    """
    Formate un pourcentage selon la locale courante.

    Args:
        value: Valeur (0.15 pour 15%)
        decimals: Nombre de décimales

    Returns:
        Pourcentage formaté
    """
    percentage = value * 100

    if _current_language == "fr":
        formatted = f"{percentage:.{decimals}f}".replace(".", ",")
        return f"{formatted} %"
    else:
        return f"{percentage:.{decimals}f}%"


class TranslationContext:
    """
    Gestionnaire de contexte pour changer temporairement la langue.

    Exemple:
        with TranslationContext("en"):
            print(tr("hello"))  # Affiche en anglais
        # Retour à la langue précédente
    """

    def __init__(self, language: str):
        self.new_language = language
        self.old_language = None

    def __enter__(self):
        self.old_language = get_language()
        set_language(self.new_language)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.old_language:
            set_language(self.old_language)
        return False


def init_i18n(language: Optional[str] = None) -> str:
    """
    Initialise le système i18n.

    Args:
        language: Code de langue (None pour détection automatique)

    Returns:
        Code de langue initialisé
    """
    if language is None:
        language = get_system_language()

    set_language(language)
    return language


def reload_translations() -> None:
    """
    Recharge toutes les traductions depuis les fichiers.
    Utile après modification des fichiers JSON.
    """
    global _translations_cache
    _translations_cache.clear()
    load_translations(_current_language)


def get_translation_keys(prefix: str = "") -> list:
    """
    Retourne toutes les clés de traduction disponibles.

    Args:
        prefix: Préfixe pour filtrer les clés

    Returns:
        Liste des clés de traduction
    """
    translations = load_translations(_current_language)

    def extract_keys(data: Dict[str, Any], current_prefix: str = "") -> list:
        keys = []
        for key, value in data.items():
            full_key = f"{current_prefix}.{key}" if current_prefix else key
            if isinstance(value, dict):
                keys.extend(extract_keys(value, full_key))
            else:
                keys.append(full_key)
        return keys

    all_keys = extract_keys(translations)

    if prefix:
        return [k for k in all_keys if k.startswith(prefix)]
    return all_keys


# Initialisation automatique au chargement du module
init_i18n()


# Export des fonctions principales
__all__ = [
    "tr",
    "tr_plural",
    "set_language",
    "get_language",
    "get_available_languages",
    "get_system_language",
    "init_i18n",
    "reload_translations",
    "format_currency",
    "format_date",
    "format_number",
    "format_percentage",
    "TranslationContext",
    "SUPPORTED_LANGUAGES",
    "DEFAULT_LANGUAGE",
]
