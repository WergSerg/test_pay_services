from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from backend.core.database import get_db
from backend.api.dependencies.auth import verify_api_key
from backend.domain.schemas.payment import PaymentCreate, PaymentResponse, PaymentDetailResponse
from backend.domain.services.payment_service import PaymentService
from backend.core.exceptions import BusinessError

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


@router.post(
    "",
    response_model=PaymentResponse,
    status_code=status.HTTP_202_ACCEPTED
)
async def create_payment(
        payment_data: PaymentCreate,
        idempotency_key: str = Header(..., alias="Idempotency-Key"),
        db: AsyncSession = Depends(get_db),
        api_key: str = Depends(verify_api_key)
):
    service = PaymentService(db)

    try:
        payment = await service.create_payment(
            idempotency_key=idempotency_key,
            amount=payment_data.amount,
            currency=payment_data.currency,
            description=payment_data.description,
            webhook_url=str(payment_data.webhook_url),
            metadata_json=payment_data.metadata_json
        )

        await db.commit()

        return payment
    except BusinessError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        await db.rollback()
        print(f"Error: {e}")  # Для отладки
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/{payment_id}",
    response_model=PaymentDetailResponse
)
async def get_payment(
        payment_id: UUID,
        db: AsyncSession = Depends(get_db),
        api_key: str = Depends(verify_api_key)
):
    """
    Get payment details by ID
    """
    service = PaymentService(db)

    try:
        payment = await service.get_payment(payment_id)
        return payment
    except BusinessError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )