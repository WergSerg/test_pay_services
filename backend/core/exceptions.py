class BusinessError(Exception):
    """Бизнес-ошибка (не требует retry)"""
    pass


class PaymentProcessingError(Exception):
    """Ошибка обработки платежа (требует retry)"""
    pass


class WebhookDeliveryError(Exception):
    """Ошибка доставки webhook"""
    pass