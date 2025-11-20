import json
import os
import re
import socket
from datetime import timedelta
from itertools import chain
from typing import Optional

try:
    import dns.resolver  # type: ignore
    import dns.exception  # type: ignore
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False

import numpy as np
import requests
from capyc.core.i18n import translation
from capyc.rest_framework.exceptions import ValidationException
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import APIException
from task_manager.core.exceptions import RetryTask

from breathecode.authenticate.models import CredentialsFacebook
from breathecode.notify.actions import send_email_message
from breathecode.services.activecampaign import ACOldClient, ActiveCampaign, ActiveCampaignClient, acp_ids, map_ids
from breathecode.services.brevo import Brevo
from breathecode.utils import getLogger

from .models import (
    AcademyAlias,
    ActiveCampaignAcademy,
    Automation,
    EmailDomainValidation,
    FormEntry,
    Tag,
)

logger = getLogger(__name__)

GOOGLE_CLOUD_KEY = os.getenv("GOOGLE_CLOUD_KEY")
MAIL_ABSTRACT_KEY = os.getenv("MAIL_ABSTRACT_KEY")

def _load_disposable_email_domains():
    """
    Carga la lista de dominios de emails desechables desde un archivo de texto.
    El archivo debe estar en breathecode/marketing/data/disposable_email_domains.txt
    Un dominio por línea, las líneas que empiezan con # son comentarios.
    
    Returns:
        set: Conjunto de dominios desechables (en minúsculas)
    
    Raises:
        FileNotFoundError: Si el archivo no existe
        IOError: Si hay un error leyendo el archivo
        Exception: Si ocurre cualquier otro error durante la carga
    
    Nota: Esta función NO tiene fallback. Si falla, se lanza una excepción
    para evitar que la validación de emails funcione sin protección contra
    correos desechables (fail-secure).
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(current_dir, "data")
    file_path = os.path.join(data_dir, "disposable_email_domains.txt")
    
    if not os.path.exists(file_path):
        error_msg = (
            f"Archivo de dominios desechables no encontrado: {file_path}. "
            "La validación de emails no puede funcionar sin este archivo."
        )
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
    
    domains = set()
    line_num = 0
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if line and not line.startswith("#"):
                    domains.add(line.lower())
    except Exception as e:
        error_msg = (
            f"Error cargando dominios desechables desde {file_path}"
            + (f" (línea {line_num})" if line_num > 0 else "")
            + f": {e}. "
            "La validación de emails no puede funcionar sin este archivo."
        )
        logger.error(error_msg)
        raise IOError(error_msg) from e
    
    if not domains:
        error_msg = (
            f"El archivo de dominios desechables está vacío: {file_path}. "
            "La validación de emails no puede funcionar sin dominios desechables."
        )
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    logger.info(f"Cargados {len(domains)} dominios desechables desde {file_path}")
    return domains


def get_disposable_email_domains():
    """
    Retorna el conjunto de dominios de emails desechables.
    Los dominios se cargan desde un archivo de texto al importar el módulo.
    """
    return DISPOSABLE_EMAIL_DOMAINS


DISPOSABLE_EMAIL_DOMAINS = _load_disposable_email_domains()

FREE_EMAIL_DOMAINS = {
    "gmail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "aol.com",
    "icloud.com",
    "mail.com",
    "protonmail.com",
    "zoho.com",
    "yandex.com",
    "gmx.com",
    "live.com",
    "msn.com",
    "inbox.com",
    "fastmail.com",
    "tutanota.com",
    "mail.ru",
    "qq.com",
    "163.com",
    "126.com",
    "sina.com",
    "rediffmail.com",
    "hushmail.com",
    "lycos.com",
    "aim.com",
    "rocketmail.com",
}

ROLE_EMAIL_PREFIXES = {
    "abuse",
    "admin",
    "administrator",
    "billing",
    "contact",
    "help",
    "info",
    "mail",
    "mailbox",
    "marketing",
    "noreply",
    "no-reply",
    "postmaster",
    "sales",
    "security",
    "support",
    "webmaster",
}


def get_save_leads():
    return os.getenv("SAVE_LEADS")


def bind_formentry_with_webhook(webhook):
    payload = json.loads(webhook.payload)

    entry = FormEntry.objects.filter(ac_deal_id=payload["deal[id]"]).order_by("-created_at").first()
    if entry is None and "deal[contactid]" in payload:
        entry = (
            FormEntry.objects.filter(ac_contact_id=payload["deal[contactid]"], ac_deal_id__isnull=True)
            .order_by("-created_at")
            .first()
        )
    if entry is None and "deal[contact_email]" in payload:
        entry = (
            FormEntry.objects.filter(email=payload["deal[contact_email]"], ac_deal_id__isnull=True)
            .order_by("-created_at")
            .first()
        )

    if entry is None:
        return False

    webhook.form_entry = entry
    webhook.save()
    return True


def _check_mx_records(domain):
    """
    Verifica si el dominio tiene registros MX válidos y los retorna.
    
    Los resultados se almacenan en la base de datos con expiración
    para evitar verificaciones repetidas del mismo dominio.
    
    Args:
        domain: Dominio a verificar
    
    Returns:
        tuple: (bool, list) - (has_mx, mx_records)
            - has_mx: True si el dominio tiene registros MX válidos
            - mx_records: Lista de servidores MX encontrados
    """
    try:
        import dns.resolver  # type: ignore
        dns_available = True
    except ImportError:
        dns_available = False
    
    try:
        cached_result = EmailDomainValidation.get_valid_domain(domain)
        if cached_result is not None:
            if dns_available and (not cached_result.mx_records or len(cached_result.mx_records) == 0):
                logger.debug(f"Cache tiene mx_records vacío pero dnspython está disponible, forzando nueva verificación para {domain}")
            else:
                return (cached_result.has_mx, cached_result.mx_records or [])
    except Exception as e:
        logger.debug(f"No se pudo acceder al cache de validaciones MX: {e}")
    
    mx_records = []
    has_mx = False
    
    try:
        if dns_available:
            answers = dns.resolver.resolve(domain, "MX")
            mx_records = [str(rdata.exchange).rstrip(".") for rdata in answers]
            has_mx = len(mx_records) > 0
        else:
            try:
                socket.gethostbyname(domain)
                has_mx = True
            except (socket.gaierror, socket.herror, Exception):
                has_mx = False
    except Exception as e:
        logger.debug(f"Error verificando registros MX para {domain}: {e}")
        has_mx = False
    
    try:
        domain_obj, _ = EmailDomainValidation.get_or_create_domain(domain)
        domain_obj.has_mx = has_mx
        domain_obj.mx_records = mx_records
        from django.utils import timezone
        domain_obj.next_check_at = timezone.now() + timedelta(days=180)
        domain_obj.save()
    except Exception as e:
        logger.debug(f"No se pudo guardar resultado de validación MX en BD: {e}")
    
    return (has_mx, mx_records)


def _check_spf(domain):
    """
    Verifica y obtiene el registro SPF del dominio.
    
    Args:
        domain: Dominio a verificar
    
    Returns:
        str o None: Registro SPF encontrado o None si no existe
    """
    try:
        import dns.resolver  # type: ignore
        import dns.exception  # type: ignore
        dns_available = True
    except ImportError:
        dns_available = False
    
    try:
        cached_result = EmailDomainValidation.get_valid_domain(domain)
        if cached_result is not None and cached_result.spf:
            return cached_result.spf
    except Exception as e:
        logger.debug(f"No se pudo acceder al cache de validaciones SPF: {e}")
    
    spf_record = None
    
    try:
        if dns_available:
            try:
                answers = dns.resolver.resolve(domain, "TXT")
                for rdata in answers:
                    txt_string = "".join([s.decode() if isinstance(s, bytes) else s for s in rdata.strings])
                    if txt_string.startswith("v=spf1"):
                        spf_record = txt_string
                        break
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.DNSException):
                pass
    except Exception as e:
        logger.debug(f"Error verificando registro SPF para {domain}: {e}")
    
    try:
        domain_obj, created = EmailDomainValidation.get_or_create_domain(domain)
        domain_obj.spf = spf_record
        # Asegurar que next_check_at tenga un valor si es un registro nuevo
        if created or domain_obj.next_check_at is None:
            from django.utils import timezone
            domain_obj.next_check_at = timezone.now() + timedelta(days=180)
        domain_obj.save()
        logger.info(f"EmailDomainValidation actualizado (SPF) para {domain}: {spf_record is not None}")
    except Exception as e:
        logger.error(f"No se pudo guardar resultado de validación SPF en BD para {domain}: {e}", exc_info=True)
    
    return spf_record


def _check_dmarc(domain):
    """
    Verifica y obtiene el registro DMARC del dominio.
    
    Args:
        domain: Dominio a verificar
    
    Returns:
        str o None: Registro DMARC encontrado o None si no existe
    """
    try:
        import dns.resolver  # type: ignore
        import dns.exception  # type: ignore
        dns_available = True
    except ImportError:
        dns_available = False
    
    try:
        cached_result = EmailDomainValidation.get_valid_domain(domain)
        if cached_result is not None and cached_result.dmarc:
            return cached_result.dmarc
    except Exception as e:
        logger.debug(f"No se pudo acceder al cache de validaciones DMARC: {e}")
    
    dmarc_record = None
    
    try:
        if dns_available:
            try:
                dmarc_domain = f"_dmarc.{domain}"
                answers = dns.resolver.resolve(dmarc_domain, "TXT")
                for rdata in answers:
                    txt_string = "".join([s.decode() if isinstance(s, bytes) else s for s in rdata.strings])
                    if txt_string.startswith("v=DMARC1"):
                        dmarc_record = txt_string
                        break
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.DNSException):
                pass
    except Exception as e:
        logger.debug(f"Error verificando registro DMARC para {domain}: {e}")
    
    try:
        domain_obj, created = EmailDomainValidation.get_or_create_domain(domain)
        domain_obj.dmarc = dmarc_record
        # Asegurar que next_check_at tenga un valor si es un registro nuevo
        if created or domain_obj.next_check_at is None:
            from django.utils import timezone
            domain_obj.next_check_at = timezone.now() + timedelta(days=180)
        domain_obj.save()
        logger.info(f"EmailDomainValidation actualizado (DMARC) para {domain}: {dmarc_record is not None}")
    except Exception as e:
        logger.error(f"No se pudo guardar resultado de validación DMARC en BD para {domain}: {e}", exc_info=True)
    
    return dmarc_record


def _calculate_quality_score(has_mx, has_spf, has_dmarc, is_role, is_free):
    """
    Calcula un score de calidad del email basado en múltiples factores.
    Retorna un valor entre 0.0 y 1.0.
    
    Nota: format_valid, is_disposable no se incluyen porque
    si alguno de estos falla, se lanza una excepción antes de llegar aquí.
    
    Args:
        has_mx: True si el dominio tiene registros MX válidos
        has_spf: True si el dominio tiene registro SPF
        has_dmarc: True si el dominio tiene registro DMARC
        is_role: True si es un email de rol (info@, support@, etc.)
        is_free: True si es un email de proveedor gratuito (gmail.com, etc.)
    
    Returns:
        float: Score entre 0.0 y 1.0
    """
    score = 1.0

    if not has_mx:
        score -= 0.3
    if not has_spf:
        score -= 0.1
    if not has_dmarc:
        score -= 0.05
    if is_role:
        score -= 0.1
    if is_free:
        score -= 0.05

    return max(0.0, min(1.0, score))


def validate_email_local(email, lang):
    """
    Replica la funcionalidad de la API de Abstract API para validación de emails.
    Realiza validaciones locales sin depender de servicios externos.

    Retorna un diccionario con información de validación:
    {
        "email": "e@mail.com",
        "user": "a",
        "domain": "mail.com",
        "format_valid": true,
        "mx_found": true,
        "mx_records": ["alt1.gmail-smtp-in.l.google.com"],
        "spf": "v=spf1 include:_spf.google.com ~all",
        "dmarc": "v=DMARC1; p=reject; ...",
        "role": false,
        "disposable": false,
        "free": false,
        "score": 0.8
    }
    """
    pattern = r"^[^@]+@[^@]+\.[^@]+$"
    format_valid = isinstance(email, str) and email and bool(re.match(pattern, email))

    if not format_valid:
        raise ValidationException(
            translation(
                lang,
                en="The email address is not valid",
                es="La dirección de correo electrónico no es válida",
                slug="email-not-valid",
            ),
            data={"email": email},
            slug="email-not-valid",
        )

    email_lower = email.lower().strip()
    split_email = email_lower.split("@")

    if len(split_email) != 2:
        raise ValidationException(
            translation(
                lang,
                en="The email address is not valid",
                es="La dirección de correo electrónico no es válida",
                slug="email-not-valid",
            ),
            data={"email": email},
            slug="email-not-valid",
        )

    user_part = split_email[0]
    domain = split_email[1]

    is_disposable = domain in DISPOSABLE_EMAIL_DOMAINS

    try:
        domain_obj, created = EmailDomainValidation.get_or_create_domain(domain)
        domain_obj.disposable = is_disposable
        if created or domain_obj.next_check_at is None:
            from django.utils import timezone
            domain_obj.next_check_at = timezone.now() + timedelta(days=180)
        domain_obj.save()
        logger.info(f"EmailDomainValidation actualizado (disposable) para {domain}: {is_disposable}")
    except Exception as e:
        logger.error(f"No se pudo actualizar campo disposable en BD para {domain}: {e}", exc_info=True)

    if is_disposable:
        raise ValidationException(
            translation(
                lang,
                en="It seems you are using a disposable email service. Please provide a different email address",
                es="Parece que estás utilizando un proveedor de correos electronicos temporales. Por favor cambia tu dirección de correo electrónico.",
                slug="disposable-email",
            ),
            slug="disposable-email",
        )

    has_mx, mx_records = _check_mx_records(domain)

    if not has_mx:
        raise ValidationException(
            translation(
                lang,
                en="The email you have provided seems invalid, please provide a different email address.",
                es="El correo electrónico que haz especificado parece inválido, por favor corrige tu correo electronico",
                slug="invalid-email",
            ),
            slug="invalid-email",
        )

    spf_record = _check_spf(domain)
    dmarc_record = _check_dmarc(domain)

    is_role = user_part in ROLE_EMAIL_PREFIXES

    is_free = domain in FREE_EMAIL_DOMAINS

    quality_score = _calculate_quality_score(
        has_mx=has_mx,
        has_spf=spf_record is not None,
        has_dmarc=dmarc_record is not None,
        is_role=is_role,
        is_free=is_free,
    )

    if quality_score <= 0.60:
        raise ValidationException(
            translation(
                lang,
                en="The email address seems to have poor quality. Are you able to provide a different email address?",
                es="El correo electrónico que haz especificado parece de mala calidad. ¿Podrías especificarnos otra dirección?",
                slug="poor-quality-email",
            ),
            data={"quality_score": quality_score},
            slug="poor-quality-email",
        )

    email_status = {
        "email": email_lower,
        "user": user_part,
        "domain": domain,
        "format_valid": format_valid,
        "mx_found": has_mx,
        "mx_records": mx_records,
        "spf": spf_record,
        "dmarc": dmarc_record,
        "role": is_role,
        "disposable": is_disposable,
        "free": is_free,
        "score": quality_score,
    }

    return email_status


def validate_email(email, lang):
    """
    Response: {
        "email": "e@mail.com",
        "did_you_mean": "",
        "user": "a",
        "domain": "mail.com",
        "format_valid": true,
        "mx_found": true,
        "smtp_check": true,
        "catch_all": false,
        "role": false,
        "disposable": false,
        "free": false,
        "score": 0.8
    }

    Error: {
        "success": false,
        "error": {
            "code": 210,
            "type": "no_email_address_supplied",
            "info": "Please specify an email address. [Example: support@apilayer.com]"
        }
    }
    """

    pattern = r"^[^@]+@[^@]+\.[^@]+$"
    if not isinstance(email, str) or not email or not re.match(pattern, email):
        raise ValidationException(
            translation(
                lang,
                en="The email address is not valid",
                es="La dirección de correo electrónico no es válida",
                slug="email-not-valid",
            ),
            data={"email": email},
        )

    resp = requests.get(
        f"https://emailvalidation.abstractapi.com/v1/?api_key={MAIL_ABSTRACT_KEY}&email={email}", timeout=10
    )
    data = resp.json()

    if "error" in data:
        if "message" in data["error"]:
            raise Exception(data["error"]["message"])

        raise ValidationException(
            translation(
                lang,
                en="Error while validating email address",
                es="Se ha producido un error validando tu dirección de correo electrónico",
                slug="email-validation-error",
            )
        )

    if "is_disposable_email" in data and data["is_disposable_email"]["value"] == True:
        raise ValidationException(
            translation(
                lang,
                en="It seems you are using a disposable email service. Please provide a different email address",
                es="Parece que estás utilizando un proveedor de correos electronicos temporales. Por favor cambia tu dirección de correo electrónico.",
                slug="disposable-email",
            )
        )

    if "is_mx_found" in data and data["is_mx_found"]["value"] == False:
        raise ValidationException(
            translation(
                lang,
                en="The email you have provided seems invalid, please provide a different email address.",
                es="El correo electrónico que haz especificado parece inválido, por favor corrige tu correo electronico",
                slug="invalid-email",
            )
        )

    if "quality_score" in data and float(data["quality_score"]) <= 0.60:
        raise ValidationException(
            translation(
                lang,
                en="The email address seems to have poor quality. Are you able to provide a different email address?",
                es="El correo electrónico que haz especificado parece de mala calidad. ¿Podrías especificarnos otra dirección?",
                slug="poor-quality-email",
            ),
            data=data,
        )

    email_quality = float(data["quality_score"])
    data["email_quality"] = email_quality
    split_email = email.split("@")

    email_status = {
        "email": email,
        "user": split_email[0],
        "domain": split_email[1],
        "format_valid": data["is_valid_format"]["value"],
        "mx_found": data["is_mx_found"]["value"],
        "smtp_check": data["is_smtp_valid"]["value"],
        "catch_all": data["is_catchall_email"]["value"],
        "role": data["is_role_email"]["value"],
        "disposable": data["is_disposable_email"]["value"],
        "free": data["is_free_email"]["value"],
        "score": email_quality,
    }

    return email_status


def set_optional(contact, key, data, custom_key=None, crm_vendor="ACTIVE_CAMPAIGN"):
    if custom_key is None:
        custom_key = key

    if crm_vendor == "ACTIVE_CAMPAIGN":
        if custom_key in data:
            contact["field[" + acp_ids[key] + ",0]"] = data[custom_key]
    else:
        if custom_key in data:
            contact[key] = data[custom_key]

    return contact


def get_lead_tags(ac_academy, form_entry):
    if "tags" not in form_entry or form_entry["tags"] == "":
        raise Exception("You need to specify tags for this entry")
    else:
        _tags = [t.strip() for t in form_entry["tags"].split(",")]
        if len(_tags) == 0 or _tags[0] == "":
            raise Exception("The contact tags are empty", 400)

    strong_tags = Tag.objects.filter(slug__in=_tags, tag_type="STRONG", ac_academy=ac_academy)
    soft_tags = Tag.objects.filter(slug__in=_tags, tag_type="SOFT", ac_academy=ac_academy)
    dicovery_tags = Tag.objects.filter(slug__in=_tags, tag_type="DISCOVERY", ac_academy=ac_academy)
    other_tags = Tag.objects.filter(slug__in=_tags, tag_type="OTHER", ac_academy=ac_academy)

    tags = list(chain(strong_tags, soft_tags, dicovery_tags, other_tags))
    if len(tags) != len(_tags):
        message = f"Some tag applied to the contact not found or have tag_type different than [STRONG, SOFT, DISCOVER, OTHER] for this academy {ac_academy.academy.name}. "
        message += f'Check for the follow tags:  {",".join(_tags)}'
        raise Exception(message)

    return tags


def get_lead_automations(ac_academy, form_entry):
    _automations = []
    if "automations" not in form_entry or form_entry["automations"] == "":
        return []
    else:
        _automations = form_entry["automations"].split(",")

    automations = Automation.objects.filter(slug__in=_automations, ac_academy=ac_academy)
    count = automations.count()
    if count == 0:
        _name = form_entry["automations"]
        raise Exception(f"The specified automation {_name} was not found for this AC Academy")

    logger.debug(f"found {str(count)} automations")
    return automations


def add_to_active_campaign(contact, academy_id: int, automation_id: int):
    if not ActiveCampaignAcademy.objects.filter(academy__id=academy_id).count():
        raise Exception(f"No academy found with id {academy_id}")

    active_campaign_academy_values = ["ac_url", "ac_key", "event_attendancy_automation__id"]
    ac_url, ac_key, event_attendancy_automation_id = (
        ActiveCampaignAcademy.objects.filter(academy__id=academy_id)
        .values_list(*active_campaign_academy_values)
        .first()
    )

    logger.info("ready to send contact with following details")
    logger.info(contact)

    old_client = ACOldClient(ac_url, ac_key)
    response = old_client.contacts.create_contact(contact)
    contact_id = response["subscriber_id"]

    if "subscriber_id" not in response:
        logger.error("error adding contact", response)
        raise APIException("Could not save contact in CRM")

    client = ActiveCampaignClient(ac_url, ac_key)

    if event_attendancy_automation_id != automation_id:
        message = "Automation doesn't exist for this AC Academy"
        logger.info(message)
        raise Exception(message)

    acp_id = Automation.objects.filter(id=automation_id).values_list("acp_id", flat=True).first()

    if not acp_id:
        message = "Automation acp_id doesn't exist"
        logger.info(message)
        raise Exception(message)

    data = {
        "contactAutomation": {
            "contact": contact_id,
            "automation": acp_id,
        }
    }

    response = client.contacts.add_a_contact_to_an_automation(data)

    if "contacts" not in response:
        logger.error(f"error triggering automation with id {str(acp_id)}", response)
        raise APIException("Could not add contact to Automation")

    logger.debug(f"Triggered automation with id {str(acp_id)}", response)


def register_new_lead(form_entry=None):
    if form_entry is None:
        raise ValidationException("You need to specify the form entry data")

    if "location" not in form_entry or form_entry["location"] is None:
        raise ValidationException("Missing location information")

    ac_academy = None
    alias = AcademyAlias.objects.filter(
        Q(active_campaign_slug=form_entry["location"]) | Q(academy__slug=form_entry["location"])
    ).first()

    try:
        if alias is not None:
            ac_academy = alias.academy.activecampaignacademy
    except Exception:
        pass

    if ac_academy is None:
        ac_academy = ActiveCampaignAcademy.objects.filter(academy__slug=form_entry["location"]).first()

    if ac_academy is None:
        raise RetryTask(
            f"No CRM vendor information for academy with slug {form_entry['location']}. Is Active Campaign or Brevo used?"
        )

    automations = get_lead_automations(ac_academy, form_entry)

    if automations:
        logger.info("found automations")
        logger.info(list(automations))
    else:
        logger.info("automations not found")

    # Tags are only for ACTIVE CAMPAIGN
    tags = []
    if ac_academy.crm_vendor == "BREVO":
        # brevo uses slugs instead of ID for automations
        if hasattr(automations, "values_list"):
            automations = automations.values_list("slug", flat=True)
        if "tags" in form_entry and len(form_entry["tags"]) > 0:
            raise Exception("Brevo CRM does not support tags, please remove them from the contact payload")
    else:
        if hasattr(automations, "values_list"):
            automations = automations.values_list("acp_id", flat=True)

        tags = get_lead_tags(ac_academy, form_entry)
        logger.info("found tags")
        logger.info(set(t.slug for t in tags))

    if (automations is None or len(automations) == 0) and len(tags) > 0:
        if tags[0].automation is None:
            raise ValidationException(
                "No automation was specified and the specified tag (if any) has no automation either"
            )

        automations = [tags[0].automation.acp_id]

    if not "email" in form_entry:
        raise ValidationException("The email doesn't exist")

    if not "first_name" in form_entry:
        raise ValidationException("The first name doesn't exist")

    if not "last_name" in form_entry:
        raise ValidationException("The last name doesn't exist")

    if not "phone" in form_entry:
        raise ValidationException("The phone doesn't exist")

    if not "id" in form_entry:
        raise ValidationException("The id doesn't exist")

    if not "course" in form_entry:
        raise ValidationException("The course doesn't exist")

    # apply default language and make sure english is "en" and not "us"
    if "utm_language" in form_entry and form_entry["utm_language"] == "us":
        form_entry["utm_language"] = "en"
    elif "language" in form_entry and form_entry["language"] == "us":
        form_entry["language"] = "en"

    contact = {
        "email": form_entry["email"],
        "first_name": form_entry["first_name"],
        "last_name": form_entry["last_name"],
        "phone": form_entry["phone"],
    }

    contact = set_optional(contact, "utm_url", form_entry, crm_vendor=ac_academy.crm_vendor)
    contact = set_optional(contact, "utm_location", form_entry, "location", crm_vendor=ac_academy.crm_vendor)
    contact = set_optional(contact, "course", form_entry, crm_vendor=ac_academy.crm_vendor)
    contact = set_optional(contact, "utm_language", form_entry, "language", crm_vendor=ac_academy.crm_vendor)
    contact = set_optional(contact, "utm_country", form_entry, "country", crm_vendor=ac_academy.crm_vendor)
    contact = set_optional(contact, "utm_campaign", form_entry, crm_vendor=ac_academy.crm_vendor)
    contact = set_optional(contact, "utm_source", form_entry, crm_vendor=ac_academy.crm_vendor)
    contact = set_optional(contact, "utm_content", form_entry, crm_vendor=ac_academy.crm_vendor)
    contact = set_optional(contact, "utm_medium", form_entry, crm_vendor=ac_academy.crm_vendor)
    contact = set_optional(contact, "utm_plan", form_entry, crm_vendor=ac_academy.crm_vendor)
    contact = set_optional(contact, "utm_placement", form_entry, crm_vendor=ac_academy.crm_vendor)
    contact = set_optional(contact, "utm_term", form_entry, crm_vendor=ac_academy.crm_vendor)
    contact = set_optional(contact, "gender", form_entry, "sex", crm_vendor=ac_academy.crm_vendor)
    contact = set_optional(contact, "client_comments", form_entry, crm_vendor=ac_academy.crm_vendor)
    contact = set_optional(contact, "gclid", form_entry, crm_vendor=ac_academy.crm_vendor)
    contact = set_optional(contact, "current_download", form_entry, crm_vendor=ac_academy.crm_vendor)
    contact = set_optional(contact, "referral_key", form_entry, crm_vendor=ac_academy.crm_vendor)

    # only for brevo
    if ac_academy.crm_vendor == "BREVO":
        contact = set_optional(contact, "utm_landing", form_entry, crm_vendor=ac_academy.crm_vendor)

    entry = FormEntry.objects.filter(id=form_entry["id"]).first()
    if not entry:
        raise ValidationException("FormEntry not found (id: " + str(form_entry["id"]) + ")")

    if len(tags) > 0 and "contact-us" == tags[0].slug:

        obj = {}
        if ac_academy.academy:
            obj["COMPANY_INFO_EMAIL"] = ac_academy.academy.feedback_email

        send_email_message(
            "new_contact",
            ac_academy.academy.marketing_email,
            {
                "subject": f"New contact from the website {form_entry['first_name']} {form_entry['last_name']}",
                "full_name": form_entry["first_name"] + " " + form_entry["last_name"],
                "client_comments": form_entry["client_comments"],
                "data": {**form_entry},
                **obj,
                # "data": { **form_entry, **address },
            },
            academy=ac_academy.academy,
        )

    is_duplicate = entry.is_duplicate(form_entry)
    if is_duplicate:
        entry.storage_status = "DUPLICATED"
        entry.save()
        logger.info("FormEntry is considered a duplicate, not sent to CRM and no automations or tags added")
        return entry

    # ENV Variable to fake lead storage
    if get_save_leads() == "FALSE":
        entry.storage_status_text = "Saved but not send to CRM because SAVE_LEADS is FALSE"
        entry.storage_status = "PERSISTED" if not is_duplicate else "DUPLICATED"
        entry.save()
        return entry

    if ac_academy.crm_vendor == "ACTIVE_CAMPAIGN":
        entry = send_to_active_campaign(entry, ac_academy, contact, automations, tags)
    elif ac_academy.crm_vendor == "BREVO":
        entry = send_to_brevo(entry, ac_academy, contact, automations)

    if entry.storage_status in ["ERROR"]:
        return entry

    entry.storage_status = "PERSISTED"
    entry.save()

    form_entry["storage_status"] = "PERSISTED"

    return entry


def send_to_active_campaign(form_entry, ac_academy, contact, automations, tags):

    old_client = ACOldClient(ac_academy.ac_url, ac_academy.ac_key)
    response = old_client.contacts.create_contact(contact)
    contact_id = response["subscriber_id"]

    # save contact_id from active campaign
    form_entry.ac_contact_id = contact_id
    form_entry.save()

    if "subscriber_id" not in response:
        logger.error("error adding contact", response)
        form_entry.storage_status = "ERROR"
        form_entry.storage_status_text = "Could not save contact in CRM: Subscriber_id not found"
        form_entry.save()
        return form_entry

    client = ActiveCampaignClient(ac_academy.ac_url, ac_academy.ac_key)
    if automations:
        for automation_id in automations:
            data = {"contactAutomation": {"contact": contact_id, "automation": automation_id}}
            response = client.contacts.add_a_contact_to_an_automation(data)

            if "contacts" not in response:
                logger.error(f"error triggering automation with id {str(automation_id)}", response)
                raise APIException("Could not add contact to Automation")
            logger.debug(f"Triggered automation with id {str(automation_id)} " + str(response))

        logger.info("automations was executed successfully")

    if tags:
        for t in tags:
            data = {"contactTag": {"contact": contact_id, "tag": t.acp_id}}
            response = client.contacts.add_a_tag_to_contact(data)
        logger.info("contact was tagged successfully")

    return form_entry


def send_to_brevo(form_entry, ac_academy, contact, automations):

    if automations.count() > 1:
        raise Exception("Only one automation at a time is allowed for Brevo")

    _a = automations.first()

    brevo_client = Brevo(ac_academy.ac_key)
    response = brevo_client.create_contact(contact, _a)

    # Brevo does not answer with the contact ID when the create_contact
    # is being made thru triggering a brevo event
    if response and "id" in response:
        form_entry.ac_contact_id = response["id"]
        form_entry.save()

    return form_entry


def test_ac_connection(ac_academy):
    client = ActiveCampaignClient(ac_academy.ac_url, ac_academy.ac_key)
    response = client.tags.list_all_tags(limit=1)
    return response


def update_deal_custom_fields(formentry_id: int):

    entry = FormEntry.objects.filter(id=formentry_id).first()
    contact_id = entry.ac_contact_id
    deal_id = entry.ac_deal_id

    if entry.academy is None or entry.academy.activecampaignacademy is None:
        raise Exception("Academy not found or not found in active campaign")
    ac_academy = entry.academy.activecampaignacademy

    client = ActiveCampaign(ac_academy.ac_key, ac_academy.ac_url)
    _incoming_values = client.get_contact_customfields(contact_id)

    # get only the right side (values) in the dict of custom fields
    _ids_to_update = [x for x in acp_ids.values() if isinstance(x, str)]
    _updated_fields = []
    for _field in _incoming_values:
        if _field["field"] not in _ids_to_update:
            logger.debug(f"Skipping contact custom field {_field['field']}")
            continue
        # convert contact custom field id to deal custom field id
        _mapped_id = map_ids(_field["field"])
        # only go thru if the deal has the respective match custom field
        if _mapped_id:
            _updated_fields.append(
                {
                    "customFieldId": _mapped_id,
                    "fieldValue": _field["value"],
                }
            )

        # deal utm_location
        _form_entry_updated = False
        if _mapped_id == "16":
            _form_entry_updated = True
            entry.ac_deal_location = _field["value"]
        # deal utm_course
        elif _mapped_id == "6":
            _form_entry_updated = True
            entry.ac_deal_course = _field["value"]

        if _form_entry_updated:
            entry.save()

    try:
        if client.update_deal(deal_id, {"fields": _updated_fields}):
            return True

    except Exception:
        logger.exception(f"There was an error updating new deal {deal_id} with its contact custom fields")
        return False


def sync_tags(ac_academy):

    if ac_academy.crm_vendor == "BREVO":
        raise Exception("Sync method has not been implemented for Brevo Tags")

    client = ActiveCampaignClient(ac_academy.ac_url, ac_academy.ac_key)
    response = client.tags.list_all_tags(limit=100)

    if "tags" not in response:
        logger.error("Invalid tags incoming from AC")
        return False

    tags = response["tags"]
    count = 0
    while len(response["tags"]) == 100:
        count = count + 100
        response = client.tags.list_all_tags(limit=100, offset=count)
        tags = tags + response["tags"]

    for tag in tags:
        t = Tag.objects.filter(slug=tag["tag"], ac_academy=ac_academy).first()
        if t is None:
            t = Tag(
                slug=tag["tag"],
                acp_id=tag["id"],
                ac_academy=ac_academy,
            )

        t.subscribers = tag["subscriber_count"]
        t.save()

    return response


def sync_automations(ac_academy):

    if ac_academy.crm_vendor == "BREVO":
        raise Exception("Sync method has not been implemented for Brevo Automations")

    client = ActiveCampaignClient(ac_academy.ac_url, ac_academy.ac_key)
    response = client.automations.list_all_automations(limit=100)

    if "automations" not in response:
        logger.error("Invalid automations incoming from AC")
        return False

    automations = response["automations"]
    count = 0
    while len(response["automations"]) == 100:
        count = count + 100
        response = client.automations.list_all_automations(limit=100, offset=count)
        if "automations" not in response:
            logger.error("Invalid automations incoming from AC pagination")
            return False
        automations = automations + response["automations"]

    for auto in automations:
        a = Automation.objects.filter(acp_id=auto["id"], ac_academy=ac_academy).first()
        if a is None:
            a = Automation(
                acp_id=auto["id"],
                ac_academy=ac_academy,
            )
        a.name = auto["name"]
        a.entered = auto["entered"]
        a.exited = auto["exited"]
        a.status = auto["status"]
        a.save()

    return response


def save_get_geolocal(contact, form_entry=None):

    if "latitude" not in form_entry or "longitude" not in form_entry:
        form_entry = contact.to_form_data()

    if "latitude" not in form_entry or "longitude" not in form_entry:
        return False
    if (
        form_entry["latitude"] == ""
        or form_entry["longitude"] == ""
        or form_entry["latitude"] is None
        or form_entry["longitude"] is None
    ):
        return False

    result = {}
    resp = requests.get(
        f"https://maps.googleapis.com/maps/api/geocode/json?latlng={form_entry['latitude']},{form_entry['longitude']}&key={GOOGLE_CLOUD_KEY}",
        timeout=2,
    )
    data = resp.json()
    if "status" in data and data["status"] == "INVALID_REQUEST":
        raise Exception(data["error_message"])

    if "results" in data:
        for address in data["results"]:
            for component in address["address_components"]:
                if "country" in component["types"] and "country" not in result:
                    result["country"] = component["long_name"]
                if "locality" in component["types"] and "locality" not in result:
                    result["locality"] = component["long_name"]
                if "route" in component["types"] and "route" not in result:
                    result["route"] = component["long_name"]
                if "postal_code" in component["types"] and "postal_code" not in result:
                    result["postal_code"] = component["long_name"]

    if "country" in result:
        contact.country = result["country"]

    if "locality" in result:
        contact.city = result["locality"]

    if "route" in result:
        contact.street_address = result["route"]

    if "postal_code" in result:
        contact.zip_code = result["postal_code"]

    contact.save()

    return True


def get_facebook_lead_info(lead_id, academy_id=None):

    now = timezone.now()

    lead = FormEntry.objects.filter(lead_id=lead_id).first()
    if lead is None:
        raise APIException(f"Invalid lead id: {lead_id}")

    credential = CredentialsFacebook.objects.filter(academy__id=academy_id, expires_at__gte=now).first()
    if credential is None:
        raise APIException("No active facebook credentials to get the leads")

    params = {"access_token": credential.token}
    resp = requests.get(f"https://graph.facebook.com/v8.0/{lead_id}/", params=params, timeout=2)
    if resp.status_code == 200:
        logger.debug("Facebook responded with 200")
        data = resp.json()
        if "field_data" in data:
            lead.utm_campaign = data["ad_id"]
            lead.utm_medium = data["ad_id"]
            lead.utm_source = "facebook"
            for field in data["field_data"]:
                if field["name"] == "first_name" or field["name"] == "full_name":
                    lead.first_name = field["values"]
                elif field["name"] == "last_name":
                    lead.last_name = field["values"]
                elif field["name"] == "email":
                    lead.email = field["values"]
                elif field["name"] == "phone":
                    lead.phone = field["values"]
            lead.save()
        else:
            logger.fatal("No information about the lead")
    else:
        logger.fatal("Impossible to connect to facebook API and retrieve lead information")


STARTS_WITH_COMMA_PATTERN = re.compile(r"^,")
ENDS_WITH_COMMA_PATTERN = re.compile(r",$")


def validate_marketing_tags(tags: str, academy_id: int, types: Optional[list] = None, lang: str = "en") -> None:
    if tags.find(",,") != -1:
        raise ValidationException(
            translation(
                lang,
                en="You can't have two commas together on tags",
                es="No puedes tener dos comas seguidas en las etiquetas",
                slug="two-commas-together",
            )
        )

    if tags.find(" ") != -1:
        raise ValidationException(
            translation(
                lang,
                en="Spaces are not allowed on tags",
                es="No se permiten espacios en los tags",
                slug="spaces-are-not-allowed",
            )
        )

    if STARTS_WITH_COMMA_PATTERN.search(tags):
        raise ValidationException(
            translation(
                lang,
                en="Tags text cannot start with comma",
                es="El texto de los tags no puede comenzar con una coma",
                slug="starts-with-comma",
            )
        )

    if ENDS_WITH_COMMA_PATTERN.search(tags):
        raise ValidationException(
            translation(
                lang,
                en="Tags text cannot ends with comma",
                es="El texto de los tags no puede terminar con una coma",
                slug="ends-with-comma",
            )
        )

    tags = [x for x in tags.split(",") if x]
    if len(tags) < 2:
        raise ValidationException(
            translation(
                lang,
                en="Event must have at least two tags",
                es="El evento debe tener al menos dos tags",
                slug="have-less-two-tags",
            )
        )

    _tags = Tag.objects.filter(slug__in=tags, ac_academy__academy__id=academy_id)
    if types:
        _tags = _tags.filter(tag_type__in=types)

    founds = set([x.slug for x in _tags])
    if len(tags) == len(founds):
        return

    not_founds = []
    for tag in tags:
        if tag not in founds:
            not_founds.append(tag)

    if len(types) == 0:
        types = ["ANY"]

    raise ValidationException(
        translation(
            lang,
            en=f'Following tags not found with types {",".join(types)}: {",".join(not_founds)}',
            es="Los siguientes tags no se encontraron con los tipos " f'{",".join(types)}: {",".join(not_founds)}',
            slug="tag-not-exist",
        )
    )


def delete_tag(tag, include_other_academies=False):

    ac_academy = tag.ac_academy
    if ac_academy is None:
        raise ValidationException(f"Invalid ac_academy for this tag {tag.slug}", code=400, slug="invalid-ac_academy")

    client = ActiveCampaign(ac_academy.ac_key, ac_academy.ac_url)
    try:
        if client.delete_tag(tag.id):
            if include_other_academies:
                Tag.objects.filter(slug=tag.slug).delete()
            else:
                tag.delete()

            return True

    except Exception:
        logger.exception(f"There was an error deleting tag for {tag.slug}")
        return False


def convert_data_frame(item):
    if "Unnamed: 0" in item:
        del item["Unnamed: 0"]
    for key in item:
        if isinstance(item[key], np.integer):
            item[key] = int(item[key])
        if isinstance(item[key], np.floating):
            item[key] = float(item[key])
        if isinstance(item[key], np.ndarray):
            item[key] = item[key].tolist()
    return item
