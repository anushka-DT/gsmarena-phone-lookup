import requests
from fastapi import APIRouter, Depends, HTTPException

from company_lookup.config import get_cache_ttl_days
from company_lookup.exceptions import ManufacturerNotFoundError
from company_lookup.services.phone_service import PhoneLookupService

router = APIRouter(prefix="/api/v1")


def get_phone_lookup_service() -> PhoneLookupService:
    """Create and return a phone lookup service."""
    return PhoneLookupService(
        cache_ttl_days=get_cache_ttl_days(),
    )


@router.get("/manufacturers")
def get_manufacturers(
    service: PhoneLookupService = Depends(get_phone_lookup_service),
) -> dict[str, dict[str, str]]:
    """Retrieve all available phone manufacturers."""
    try:
        manufacturers = service.get_manufacturers()
        return {"manufacturers": manufacturers}

    except requests.RequestException as error:
        raise HTTPException(
            status_code=503,
            detail="GSMArena is temporarily unavailable.",
        ) from error


@router.get("/phones")
def get_phones(
    brand: str,
    service: PhoneLookupService = Depends(get_phone_lookup_service),
) -> dict[str, str | list[dict[str, str]]]:
    """Retrieve all phones belonging to a manufacturer."""
    brand = brand.strip()

    try:
        phones = service.get_phones(brand)

        return {
            "brand": brand,
            "phones": phones,
        }

    except ManufacturerNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error

    except requests.RequestException as error:
        raise HTTPException(
            status_code=503,
            detail="GSMArena is temporarily unavailable.",
        ) from error


@router.get("/phones/specifications")
def get_phone_specifications(
    brand: str,
    model: str,
    service: PhoneLookupService = Depends(get_phone_lookup_service),
) -> dict[str, str | dict[str, dict[str, list[str]]]]:
    """Retrieve specifications for a particular phone model."""
    brand = brand.strip()
    model = model.strip()

    try:
        phones = service.get_phones(brand)

        requested_model = model.casefold()

        phone = next(
            (
                phone
                for phone in phones
                if phone["name"].strip().casefold() == requested_model
            ),
            None,
        )

        if phone is None:
            raise HTTPException(
                status_code=404,
                detail=f"Phone model '{model}' was not found for '{brand}'.",
            )

        specifications = service.get_phone_specifications(phone["url"])

        return {
            "brand": brand,
            "model": phone["name"],
            "specifications": specifications,
        }

    except ManufacturerNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error

    except requests.RequestException as error:
        raise HTTPException(
            status_code=503,
            detail="GSMArena is temporarily unavailable.",
        ) from error
